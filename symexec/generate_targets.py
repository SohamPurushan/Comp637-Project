"""
generate_targets.py
~~~~~~~~~~~~~~~~~~~~
Reads results/triaged_warnings.json and results/clang_warnings.json and
produces symexec/targets.json — the manifest that verify_klee.py consumes.

For each warning where llm_decision is "likely_true" or "uncertain", this
script generates a TargetSpec by inspecting the flagged C source file to
infer the enclosing function name, return type, and parameters.

The simple approach used here: find the nearest function definition above the
warning line using a regex.  This is pilot-scope accuracy — it covers the
common cases in the SARD / Juliet CWE-476 benchmarks cleanly.

Usage:
    python symexec/generate_targets.py
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DEFAULT_ANALYZER_OUTPUT,
    DEFAULT_TRIAGE_OUTPUT,
    TARGETS_MANIFEST,
)

# ---------------------------------------------------------------------------
# Argument kind inference
# ---------------------------------------------------------------------------
# Map from C type string fragments → kind label used in verify_klee.py
_KIND_MAP = [
    (re.compile(r"\bchar\s*\*"), "char_ptr"),  # not yet supported, skip
    (re.compile(r"\bint\s*\*"), "int_ptr"),
    (re.compile(r"\bchar\b"), "char"),
    (re.compile(r"\bint\b"), "int"),
]

SUPPORTED_KINDS = {"int", "char", "int_ptr"}


def infer_kind(c_type: str) -> Optional[str]:
    for pattern, kind in _KIND_MAP:
        if pattern.search(c_type):
            return kind
    return None


# ---------------------------------------------------------------------------
# Function signature extraction
# ---------------------------------------------------------------------------
# Regex that matches a C function definition opening line, capturing:
#   group 1 → return type
#   group 2 → function name
#   group 3 → parameter list (raw)
_FUNC_DEF_RE = re.compile(
    r"^([\w\s\*]+?)\s+"          # return type (greedy, with optional *)
    r"(\w+)\s*"                  # function name
    r"\(([^)]*)\)\s*\{?\s*$",    # parameter list
    re.MULTILINE,
)

_PARAM_RE = re.compile(
    r"((?:const\s+)?(?:unsigned\s+)?(?:int|char|void|long|short|float|double)\s*\*?)\s+(\w+)"
)


def parse_params(param_str: str) -> List[Dict[str, str]]:
    """Parse a raw parameter list string into [{name, kind}, ...]."""
    if not param_str.strip() or param_str.strip() in {"void", ""}:
        return []
    params = []
    for part in param_str.split(","):
        m = _PARAM_RE.search(part.strip())
        if m:
            c_type = m.group(1).strip()
            name = m.group(2).strip()
            kind = infer_kind(c_type)
            if kind and kind in SUPPORTED_KINDS:
                params.append({"name": name, "kind": kind})
    return params


def find_enclosing_function(source_path: Path, warning_line: int):
    """Return (function_name, return_type, params) for the function that
    contains warning_line, or None if not found."""
    try:
        lines = source_path.read_text(errors="replace").splitlines()
    except Exception:
        return None

    # Work with 1-based warning_line, but Python lists are 0-based
    idx = min(max(warning_line - 1, 0), len(lines) - 1)

    bad = {"if", "for", "while", "switch", "return", "else"}

    # Scan upward line by line, looking for something that looks like
    # a function definition header. This is more robust than applying
    # one big regex over a chunk of text.
    for i in range(idx, max(-1, idx - 80), -1):
        line = lines[i].strip()

        if not line:
            continue
        if line.startswith("#"):
            continue

        # Match forms like:
        #   void foo()
        #   int *foo(int x)
        # and allow the brace either on the same line or the next line.
        m = re.match(r"^([\w\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*$", line)
        if m is None:
            m = re.match(r"^([\w\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*\{\s*$", line)

        if m is None:
            continue

        ret_type = m.group(1).strip()
        func_name = m.group(2).strip()
        param_str = m.group(3).strip()

        if func_name in bad or ret_type.rstrip("* ") in bad:
            continue

        params = parse_params(param_str)
        return func_name, ret_type, params

    return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not DEFAULT_TRIAGE_OUTPUT.exists():
        print(f"ERROR: Triage output not found: {DEFAULT_TRIAGE_OUTPUT}")
        print("Run  python llm_triage/triage.py  first.")
        sys.exit(1)

    if not DEFAULT_ANALYZER_OUTPUT.exists():
        print(f"ERROR: Analyzer output not found: {DEFAULT_ANALYZER_OUTPUT}")
        print("Run  python analyzer/run_clang_analyzer.py  first.")
        sys.exit(1)

    triage: List[Dict[str, Any]] = json.loads(DEFAULT_TRIAGE_OUTPUT.read_text())
    warnings_raw: List[Dict[str, Any]] = json.loads(DEFAULT_ANALYZER_OUTPUT.read_text())
    warning_map = {w["warning_id"]: w for w in warnings_raw}

    targets: List[Dict[str, Any]] = []
    skipped = 0

    for t in triage:
        if t["llm_decision"] not in {"likely_true", "uncertain"}:
            continue

        wid = t["warning_id"]
        w = warning_map.get(wid)
        if w is None:
            skipped += 1
            continue

        raw_path = Path(w["file"])

        candidate_paths = [
            PROJECT_ROOT / raw_path,
            PROJECT_ROOT / "data" / "pilot" / raw_path.name,
            PROJECT_ROOT / "data" / "juliet" / raw_path.name,
        ]

        source_path = next((p for p in candidate_paths if p.exists()), None)
        if source_path is None:
            skipped += 1
            continue

        result = find_enclosing_function(source_path, w["line"])
        if result is None:
            skipped += 1
            continue

        func_name, ret_type, params = result

        # If we could not parse any supported params, still add with empty args
        # so verify_klee can at least attempt a no-arg harness.
        targets.append(
            {
                "warning_id": wid,
                "source_file": str(source_path),
                "target_file": str(source_path),
                "target_line": w["line"],
                "function_name": func_name,
                "return_type": ret_type,
                "arguments": params,
            }
        )

    TARGETS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    TARGETS_MANIFEST.write_text(json.dumps(targets, indent=2))

    print(f"Generated {len(targets)} target specs → {TARGETS_MANIFEST}")
    if skipped:
        print(f"Skipped {skipped} warnings (source not found or function not parsed)")


if __name__ == "__main__":
    main()
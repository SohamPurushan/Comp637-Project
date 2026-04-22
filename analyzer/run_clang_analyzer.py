"""
run_clang_analyzer.py
~~~~~~~~~~~~~~~~~~~~~~
Runs Clang Static Analyzer (scan-build / clang --analyze) on every C file
in the chosen dataset directory and produces a structured JSON file at
results/clang_warnings.json.

Each record in the output corresponds to one warning and carries:
  warning_id, file, line, column, message, checker, category,
  code_context  (±5 lines around the flagged line)

Usage:
    python analyzer/run_clang_analyzer.py --dataset pilot
    python analyzer/run_clang_analyzer.py --dataset juliet

Requires:  clang (system or Homebrew LLVM)
"""

import argparse
import hashlib
import json
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    CLANG_BIN,
    DEFAULT_ANALYZER_OUTPUT,
    JULIET_DIR,
    PILOT_DIR,
    RESULTS_DIR,
    TARGET_BUG_CLASS,
)

# Clang checkers most relevant to CWE-476 null pointer dereference
ENABLED_CHECKERS = [
    "core.NullDereference",
    "core.NonNullParamChecker",
    "alpha.core.NullDereference",
]

# How many source lines to include as context either side of the warning
CONTEXT_LINES = 5


# ---------------------------------------------------------------------------
# Warning ID generation
# ---------------------------------------------------------------------------
def make_warning_id(file: str, line: int, checker: str, idx: int) -> str:
    raw = f"{file}:{line}:{checker}:{idx}"
    return "W" + hashlib.sha1(raw.encode()).hexdigest()[:7].upper()


# ---------------------------------------------------------------------------
# Code context extraction
# ---------------------------------------------------------------------------
def extract_context(source_file: Path, line: int, n: int = CONTEXT_LINES) -> List[str]:
    try:
        lines = source_file.read_text(errors="replace").splitlines()
    except Exception:
        return []
    start = max(0, line - 1 - n)
    end = min(len(lines), line - 1 + n + 1)
    return [f"{start + i + 1:4d}  {lines[start + i]}" for i in range(end - start)]


# ---------------------------------------------------------------------------
# Invoke clang --analyze on a single file and return parsed plist data
# ---------------------------------------------------------------------------
def analyze_file(c_file: Path, plist_dir: Path) -> Optional[dict]:
    plist_out = plist_dir / (c_file.stem + ".plist")

    # Build command
    # -Xclang -analyzer-checker=... enables specific checkers
    checker_args: List[str] = []
    for checker in ENABLED_CHECKERS:
        checker_args += ["-Xclang", f"-analyzer-checker={checker}"]

    cmd = [
        CLANG_BIN,
        "--analyze",
        "-Xclang", "-analyzer-output=plist",
        "-o", str(plist_out),
        *checker_args,
        "-Xclang", "-analyzer-config",
        "-Xclang", "aggressive-binary-operation-simplification=true",
        str(c_file),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if not plist_out.exists():
        return None

    try:
        with open(plist_out, "rb") as fh:
            return plistlib.load(fh)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Parse plist → list of warning dicts
# ---------------------------------------------------------------------------
def plist_to_warnings(
    plist_data: dict,
    source_root: Path,
    counter_start: int,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    files = plist_data.get("files", [])
    diagnostics = plist_data.get("diagnostics", [])

    for idx, diag in enumerate(diagnostics, start=counter_start):
        location = diag.get("location", {})
        file_idx = location.get("file", 0)
        line = location.get("line", 0)
        col = location.get("col", 0)

        file_str = files[file_idx] if file_idx < len(files) else "unknown"
        file_path = Path(file_str)

        checker = diag.get("check_name", "unknown")
        message = diag.get("description", "")
        category = diag.get("category", "")

        wid = make_warning_id(file_str, line, checker, idx)
        context = extract_context(file_path, line)

        records.append(
            {
                "warning_id": wid,
                "file": str(file_path.relative_to(source_root))
                if file_path.is_relative_to(source_root)
                else file_str,
                "line": line,
                "column": col,
                "message": message,
                "checker": checker,
                "category": category,
                "code_context": context,
            }
        )
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_on_directory(source_dir: Path) -> List[Dict[str, Any]]:
    c_files = sorted(source_dir.rglob("*.c"))
    if not c_files:
        print(f"  No .c files found in {source_dir}")
        return []

    print(f"  Found {len(c_files)} C files in {source_dir}")
    all_warnings: List[Dict[str, Any]] = []
    counter = 0

    with tempfile.TemporaryDirectory() as tmp:
        plist_dir = Path(tmp)
        for i, c_file in enumerate(c_files, 1):
            print(f"  [{i}/{len(c_files)}] {c_file.name}", end="\r", flush=True)
            plist_data = analyze_file(c_file, plist_dir)
            if plist_data is None:
                continue
            records = plist_to_warnings(plist_data, PROJECT_ROOT, counter)
            counter += len(records)
            all_warnings.extend(records)

    print()  # newline after \r progress
    return all_warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Clang Static Analyzer on dataset")
    parser.add_argument(
        "--dataset",
        choices=["pilot", "juliet"],
        default="pilot",
        help="Which dataset to analyze (default: pilot)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_ANALYZER_OUTPUT,
        help="Output JSON file path",
    )
    args = parser.parse_args()

    source_dir = PILOT_DIR if args.dataset == "pilot" else JULIET_DIR

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        print("Run  python dataset/prepare_pilot.py  or  python dataset/prepare_juliet.py  first.")
        sys.exit(1)

    print(f"=== Clang Static Analyzer ({TARGET_BUG_CLASS}) ===")
    print(f"  Dataset : {args.dataset}")
    print(f"  Source  : {source_dir}")
    print(f"  Output  : {args.out}\n")

    warnings = run_on_directory(source_dir)

    # Deduplicate by (file, line, checker)
    seen = set()
    unique: List[Dict[str, Any]] = []
    for w in warnings:
        key = (w["file"], w["line"], w["checker"])
        if key not in seen:
            seen.add(key)
            unique.append(w)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(unique, indent=2))
    print(f"Wrote {len(unique)} unique warnings → {args.out}")


if __name__ == "__main__":
    main()

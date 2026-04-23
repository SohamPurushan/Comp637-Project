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
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

ENABLED_CHECKERS = [
    "core.NullDereference",
    "core.NonNullParamChecker",
]

CONTEXT_LINES = 5

# Very lightweight filename filter for the pilot set.
# This helps avoid analyzing unrelated bug families like use-after-free
# when the whole project is scoped to CWE-476.
NULL_FILE_HINTS = (
    "null",
    "nullptr",
    "nullpointer",
    "null_pointer",
    "null-deref",
    "null_deref",
)


def make_warning_id(file: str, line: int, checker: str, idx: int) -> str:
    raw = f"{file}:{line}:{checker}:{idx}"
    return "W" + hashlib.sha1(raw.encode()).hexdigest()[:7].upper()


def extract_context(source_file: Path, line: int, n: int = CONTEXT_LINES) -> List[str]:
    try:
        lines = source_file.read_text(errors="replace").splitlines()
    except Exception:
        return []

    start = max(0, line - 1 - n)
    end = min(len(lines), line - 1 + n + 1)
    return [f"{start + i + 1:4d} {lines[start + i]}" for i in range(end - start)]


def parse_text_diagnostics(stderr_text: str, c_file: Path, counter_start: int) -> List[Dict[str, Any]]:
    """
    Fallback parser for clang text diagnostics, e.g.
    /path/file.c:12:8: warning: Dereference of null pointer [core.NullDereference]
    """
    records: List[Dict[str, Any]] = []
    pattern = re.compile(
        r"^(.*?):(\d+):(\d+):\s+warning:\s+(.*?)\s+\[(.*?)\]\s*$",
        re.MULTILINE,
    )

    idx = counter_start
    for match in pattern.finditer(stderr_text):
        file_str, line_s, col_s, message, checker = match.groups()

        # Keep only the actual Clang Static Analyzer null-deref checkers
        if checker not in ENABLED_CHECKERS:
            continue

        file_path = Path(file_str)
        line = int(line_s)
        col = int(col_s)

        idx += 1
        records.append(
            {
                "warning_id": make_warning_id(file_str, line, checker, idx),
                "file": str(file_path.relative_to(PROJECT_ROOT))
                if file_path.is_absolute() and file_path.is_relative_to(PROJECT_ROOT)
                else file_str,
                "line": line,
                "column": col,
                "message": message,
                "checker": checker,
                "category": "",
                "code_context": extract_context(file_path, line),
            }
        )

    return records


def analyze_file(c_file: Path, plist_dir: Path) -> Tuple[Optional[dict], str, str, int]:
    plist_out = plist_dir / (c_file.stem + ".plist")

    checker_args: List[str] = []
    for checker in ENABLED_CHECKERS:
        checker_args += ["-Xclang", f"-analyzer-checker={checker}"]

    cmd = [
        CLANG_BIN,
        "--analyze",
        "-x", "c",
        "-std=c11",
        "-Wno-everything",
        "-Xclang", "-analyzer-output=plist",
        "-o", str(plist_out),
        *checker_args,
        str(c_file),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    plist_data = None
    if plist_out.exists():
        try:
            with open(plist_out, "rb") as fh:
                plist_data = plistlib.load(fh)
        except Exception:
            plist_data = None

    return plist_data, result.stdout, result.stderr, result.returncode


def plist_to_warnings(
    plist_data: dict,
    source_root: Path,
    counter_start: int,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    files = plist_data.get("files", [])
    diagnostics = plist_data.get("diagnostics", [])

    for idx, diag in enumerate(diagnostics, start=counter_start + 1):
        location = diag.get("location", {})
        file_idx = location.get("file", 0)
        line = location.get("line", 0)
        col = location.get("col", 0)

        file_str = files[file_idx] if file_idx < len(files) else "unknown"
        file_path = Path(file_str)

        checker = diag.get("check_name", "unknown")
        message = diag.get("description", "")
        category = diag.get("category", "")

        records.append(
            {
                "warning_id": make_warning_id(file_str, line, checker, idx),
                "file": str(file_path.relative_to(source_root))
                if file_path.is_absolute() and file_path.is_relative_to(source_root)
                else file_str,
                "line": line,
                "column": col,
                "message": message,
                "checker": checker,
                "category": category,
                "code_context": extract_context(file_path, line),
            }
        )

    return records


def choose_files(source_dir: Path, dataset_name: str) -> List[Path]:
    c_files = sorted(source_dir.rglob("*.c"))

    if dataset_name == "pilot":
        filtered = [
            f for f in c_files
            if any(hint in f.name.lower() for hint in NULL_FILE_HINTS)
        ]
        if filtered:
            return filtered

    return c_files


def run_on_directory(source_dir: Path, dataset_name: str) -> List[Dict[str, Any]]:
    c_files = choose_files(source_dir, dataset_name)
    if not c_files:
        print(f"No .c files found in {source_dir}")
        return []

    print(f"Found {len(c_files)} C files in {source_dir}")

    all_warnings: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    counter = 0

    with tempfile.TemporaryDirectory() as tmp:
        plist_dir = Path(tmp)

        for i, c_file in enumerate(c_files, 1):
            print(f"[{i}/{len(c_files)}] {c_file.name}", end="\r", flush=True)

            plist_data, stdout_text, stderr_text, returncode = analyze_file(c_file, plist_dir)

            file_records: List[Dict[str, Any]] = []
            if plist_data is not None:
                file_records = plist_to_warnings(plist_data, PROJECT_ROOT, counter)

            if not file_records and stderr_text:
                file_records = parse_text_diagnostics(stderr_text, c_file, counter)

            if file_records:
                counter += len(file_records)
                all_warnings.extend(file_records)
            elif returncode != 0:
                failures.append(
                    {
                        "file": str(c_file),
                        "returncode": returncode,
                        "stderr": stderr_text[:1000],
                    }
                )

    print()

    debug_path = RESULTS_DIR / "clang_failures.json"
    debug_path.write_text(json.dumps(failures, indent=2))
    print(f"Wrote {len(failures)} analyzer failure record(s) → {debug_path}")

    return all_warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Clang Static Analyzer on dataset")
    parser.add_argument(
        "--dataset",
        choices=["pilot", "juliet"],
        default="pilot",
        help="Which dataset to analyze",
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
        print("Run python3 dataset/prepare_pilot.py or python3 dataset/prepare_juliet.py first.")
        sys.exit(1)

    print(f"=== Clang Static Analyzer ({TARGET_BUG_CLASS}) ===")
    print(f"  Dataset : {args.dataset}")
    print(f"  Source  : {source_dir}")
    print(f"  Output  : {args.out}\n")

    warnings = run_on_directory(source_dir, args.dataset)

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
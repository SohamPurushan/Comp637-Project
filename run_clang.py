import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List

from config import CLANG_BIN, DEFAULT_ANALYZER_OUTPUT, DEFAULT_SOURCE_DIR
from schemas import WarningRecord


WARNING_RE = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+):(?P<column>\d+):\s+warning:\s+"
    r"(?P<message>.*?)\s+\[(?P<checker>[^\]]+)\]$"
)


def choose_clang_binary() -> str:
    configured = Path(CLANG_BIN)
    if configured.exists():
        return str(configured)

    fallback = shutil.which("clang")
    if fallback:
        return fallback

    raise FileNotFoundError(
        f"Could not find clang. Checked configured path '{CLANG_BIN}' "
        f"and PATH lookup for 'clang'."
    )


def discover_source_files(source_dir: Path) -> List[Path]:
    extensions = {".c", ".cc", ".cpp", ".cxx"}
    files = sorted(
        p for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in extensions
    )
    return files


def run_clang_analyzer(clang_bin: str, source_file: Path) -> str:
    cmd = [
        clang_bin,
        "--analyze",
        "-Xanalyzer",
        "-analyzer-output=text",
        str(source_file),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    # Clang warnings typically go to stderr.
    # Keep stdout too in case a platform emits there.
    combined_output = "\n".join(
        chunk for chunk in [result.stdout.strip(), result.stderr.strip()] if chunk
    )
    return combined_output


def make_warning_id(
    source_file: str,
    line: int,
    column: int,
    checker: str,
    message: str,
) -> str:
    raw = f"{source_file}:{line}:{column}:{checker}:{message}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"warn_{digest}"


def infer_category(checker: str) -> str:
    # Example: core.NullDereference -> core
    if "." in checker:
        return checker.split(".", 1)[0]
    return checker


def parse_warnings(analyzer_output: str) -> List[WarningRecord]:
    warnings: List[WarningRecord] = []

    for line in analyzer_output.splitlines():
        match = WARNING_RE.match(line.strip())
        if not match:
            continue

        file_path = match.group("file")
        line_no = int(match.group("line"))
        column_no = int(match.group("column"))
        message = match.group("message")
        checker = match.group("checker")
        category = infer_category(checker)

        warning_id = make_warning_id(
            source_file=file_path,
            line=line_no,
            column=column_no,
            checker=checker,
            message=message,
        )

        warnings.append(
            WarningRecord(
                warning_id=warning_id,
                file=file_path,
                line=line_no,
                column=column_no,
                message=message,
                checker=checker,
                category=category,
            )
        )

    return warnings


def analyze_source_file(clang_bin: str, source_file: Path) -> List[WarningRecord]:
    output = run_clang_analyzer(clang_bin, source_file)
    return parse_warnings(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Clang Static Analyzer on pilot C/C++ files and emit warning JSON."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Directory containing source files to analyze.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ANALYZER_OUTPUT,
        help="Path to write clang_warnings.json.",
    )
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_path = args.output.resolve()

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    clang_bin = choose_clang_binary()
    source_files = discover_source_files(source_dir)

    if not source_files:
        print(f"No C/C++ source files found under {source_dir}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("[]")
        return

    all_warnings: List[WarningRecord] = []

    print(f"Using clang: {clang_bin}")
    print(f"Analyzing {len(source_files)} source file(s) under {source_dir}")

    for source_file in source_files:
        file_warnings = analyze_source_file(clang_bin, source_file)
        all_warnings.extend(file_warnings)
        print(f"- {source_file.name}: {len(file_warnings)} warning(s)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([w.model_dump() for w in all_warnings], indent=2)
    )

    print(f"Wrote {len(all_warnings)} warning(s) to {output_path}")


if __name__ == "__main__":
    main()
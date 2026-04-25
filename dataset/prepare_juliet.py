"""
prepare_juliet.py
~~~~~~~~~~~~~~~~~
Filters the NIST Juliet C/C++ 1.3.1 test suite down to CWE-476
(null pointer dereference) cases only, and writes a ground-truth manifest.

Expected layout after download:
    data/downloads/juliet_cpp_1.3.1.zip

Downloaded from:
    https://samate.nist.gov/SARD/downloads/test-suites/2017-10-01-juliet-test-suite-for-c-cplusplus-v1-3-1-with-extra-support.zip

Usage:
    python dataset/prepare_juliet.py
"""

import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
JULIET_DIR = DATA_DIR / "juliet"
DOWNLOAD_DIR = DATA_DIR / "downloads"

JULIET_URL = (
    "https://samate.nist.gov/SARD/downloads/test-suites/"
    "2022-08-11-juliet-c-cplusplus-v1-3-1-with-extra-support.zip"
)
JULIET_ZIP = DOWNLOAD_DIR / "juliet_cpp_1.3.1.zip"

# The CWE directory name inside the Juliet archive
CWE476_DIR_NAME = "CWE476_NULL_Pointer_Dereference"


def download_if_missing(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  Already downloaded: {dest.name}")
        return
    print(f"  Downloading Juliet 1.3.1 (~300 MB) …")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  Saved to {dest}")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        print(
            "  Please download Juliet 1.3.1 manually from:\n"
            "    https://samate.nist.gov/SARD/test-suites/116\n"
            f"  and place the ZIP at:\n    {JULIET_ZIP}"
        )
        sys.exit(1)


def extract_cwe476(zip_path: Path, out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.rglob("*.c")):
        print(f"  Already extracted: {out_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    print("  Extracting CWE476 files …")

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        # 1) Extract CWE-476 testcase files
        cwe_members = [
            m for m in names
            if CWE476_DIR_NAME in m and (m.endswith(".c") or m.endswith(".cpp") or m.endswith(".h"))
        ]

        # 2) Extract Juliet support files that the testcases include
        support_members = [
            m for m in names
            if (
                "testcasesupport/" in m
                or m.endswith("/std_testcase.h")
                or m.endswith("/std_testcase_io.h")
                or m.endswith("/io.c")
                or m.endswith("/io.h")
            )
        ]

        members = sorted(set(cwe_members + support_members))

        if not cwe_members:
            print(
                f"  WARNING: No files matching '{CWE476_DIR_NAME}' found in archive.\n"
                "  Archive structure may differ. Check the ZIP and update CWE476_DIR_NAME."
            )

        for member in members:
            zf.extract(member, out_dir)

    print(f"  Extracted {len(cwe_members)} CWE476 files and {len(support_members)} support files.")

def classify_file(path_str):
    p = str(path_str).replace("\\", "/")

    # Only label actual CWE476 testcase source files
    if "CWE476_NULL_Pointer_Dereference" not in p:
        return None

    if "/testcasesupport/" in p:
        return None

    if not p.endswith(".c"):
        return None

    return 1

def build_ground_truth(root: Path):
    gt = {}
    bug_count = 0
    safe_count = 0

    for c_file in sorted(root.rglob("*.c")):
        label = classify_file(c_file)
        if label is None:
            continue

        key = str(c_file.relative_to(PROJECT_ROOT)).replace("\\", "/")
        gt[key] = {
            "label": label,
            "suite": "juliet_cwe476",
        }

        if label == 1:
            bug_count += 1
        elif label == 0:
            safe_count += 1

    print(f"Wrote ground truth for {len(gt)} files → {root / 'ground_truth.json'}")
    print(f"  Bug files  : {bug_count}")
    print(f"  Safe files : {safe_count}")
    return gt


def main() -> None:
    print("=== Juliet CWE-476 Dataset Preparation ===\n")
    download_if_missing(JULIET_URL, JULIET_ZIP)
    extract_cwe476(JULIET_ZIP, JULIET_DIR)

    gt = build_ground_truth(JULIET_DIR)
    gt_path = JULIET_DIR / "ground_truth.json"
    gt_path.write_text(json.dumps(gt, indent=2))
    print(f"\nWrote ground truth for {len(gt)} files → {gt_path}")
    bug_count = sum(1 for v in gt.values() if v["label"] == 1)
    safe_count = sum(1 for v in gt.values() if v["label"] == 0)
    print(f"  Bug files  : {bug_count}")
    print(f"  Safe files : {safe_count}")
    print("Juliet CWE-476 dataset ready.\n")


if __name__ == "__main__":
    main()

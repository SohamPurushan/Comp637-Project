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
    print(f"  Extracting CWE476 files …")
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [
            m for m in zf.namelist()
            if CWE476_DIR_NAME in m and (m.endswith(".c") or m.endswith(".cpp") or m.endswith(".h"))
        ]
        if not members:
            print(
                f"  WARNING: No files matching '{CWE476_DIR_NAME}' found in archive.\n"
                "  Archive structure may differ. Check the ZIP and update CWE476_DIR_NAME."
            )
        for member in members:
            zf.extract(member, out_dir)
    print(f"  Extracted {len(members)} files.")


def classify_file(path: Path) -> int:
    """
    Juliet naming convention:
      *_good*.c  or  *_00.c  → label 0 (no bug)
      *_bad*.c   or  *_01.c  → label 1 (bug present)
    """
    name = path.name.lower()
    if "_good" in name or name.endswith("_00.c"):
        return 0
    if "_bad" in name or "_01" in name:
        return 1
    # Helper files / shared infrastructure — exclude from benchmark
    return -1


def build_ground_truth(juliet_dir: Path) -> dict:
    gt: dict = {}
    for c_file in sorted(juliet_dir.rglob("*.c")):
        label = classify_file(c_file)
        if label == -1:
            continue  # skip support/helper files
        rel = str(c_file.relative_to(PROJECT_ROOT))
        gt[rel] = {"label": label, "suite": "juliet_cwe476"}
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

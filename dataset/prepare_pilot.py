"""
prepare_pilot.py
~~~~~~~~~~~~~~~~
Downloads the two NIST SARD C test suites used for the pilot benchmark:

  • C Test Suite for Source Code Analyzer - Secure v2
    (ground-truth label: no bug  → label = 0)
  • C Test Suite for Source Code Analyzer v2 - Vulnerable
    (ground-truth label: bug present → label = 1)

Extracts them into  data/pilot/secure/  and  data/pilot/vulnerable/
and writes  data/pilot/ground_truth.json  mapping each C file to its label.

Usage:
    python dataset/prepare_pilot.py
"""

import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# --------------------------------------------------------------------------- #
# NIST SARD download URLs (direct ZIP links as of 2025)                        #
# If these change, update them or download manually and place the ZIPs in      #
# data/downloads/ before running.                                               #
# --------------------------------------------------------------------------- #
PILOT_DOWNLOADS = {
    "secure": {
        "url": "https://samate.nist.gov/SARD/downloads/test-suites/2015-03-15-c-test-suite-for-source-code-analyzer-secure-vv2.zip",
        "label": 0,
        "dest": "secure",
    },
    "vulnerable": {
        "url": "https://samate.nist.gov/SARD/downloads/test-suites/2015-03-15-c-test-suite-for-source-code-analyzer-v2-vulnerable.zip",
        "label": 1,
        "dest": "vulnerable",
    },
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PILOT_DIR = DATA_DIR / "pilot"
DOWNLOAD_DIR = DATA_DIR / "downloads"


def download_if_missing(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  Already downloaded: {dest.name}")
        return
    print(f"  Downloading {url} …")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  Saved to {dest}")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        print(
            "  Please download the file manually and place it at:\n"
            f"    {dest}\n"
            "  Then re-run this script."
        )
        sys.exit(1)


def extract_zip(zip_path: Path, out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"  Already extracted: {out_dir}")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Extracting {zip_path.name} → {out_dir} …")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)


def build_ground_truth(pilot_dir: Path) -> dict:
    """Walk secure/ and vulnerable/ and map every .c file to its label."""
    gt: dict = {}
    for suite, info in PILOT_DOWNLOADS.items():
        suite_dir = pilot_dir / info["dest"]
        for c_file in sorted(suite_dir.rglob("*.c")):
            rel = str(c_file.relative_to(PROJECT_ROOT))
            gt[rel] = {"label": info["label"], "suite": suite}
    return gt


def main() -> None:
    print("=== NIST SARD Pilot Dataset Preparation ===\n")

    for key, info in PILOT_DOWNLOADS.items():
        zip_path = DOWNLOAD_DIR / f"sard_{key}_v2.zip"
        out_dir = PILOT_DIR / info["dest"]

        print(f"[{key.upper()}]")
        download_if_missing(info["url"], zip_path)
        extract_zip(zip_path, out_dir)

    gt = build_ground_truth(PILOT_DIR)
    gt_path = PILOT_DIR / "ground_truth.json"
    gt_path.write_text(json.dumps(gt, indent=2))
    print(f"\nWrote ground truth for {len(gt)} files → {gt_path}")

    # Keep the hand-crafted example files as well
    print("Pilot dataset ready.\n")


if __name__ == "__main__":
    main()

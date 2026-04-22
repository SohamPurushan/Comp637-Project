"""
pipeline.py
~~~~~~~~~~~
Merges all three pipeline stages into a single results file.

Stages merged:
  1. Clang Static Analyzer   → results/clang_warnings.json
  2. Qwen2.5 LLM triage      → results/triaged_warnings.json
  3. KLEE symbolic execution  → results/klee_runs/symexec_results.json

Output: results/pipeline_results.json
  Each record contains: warning, triage, symexec, ground_truth, final_decision

Usage:
    python pipeline.py --dataset pilot
    python pipeline.py --dataset juliet
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DATA_DIR,
    DEFAULT_ANALYZER_OUTPUT,
    DEFAULT_FINAL_OUTPUT,
    DEFAULT_TRIAGE_OUTPUT,
    JULIET_DIR,
    KLEE_RUNS_DIR,
    PILOT_DIR,
)


# ---------------------------------------------------------------------------
# Ground-truth loading
# ---------------------------------------------------------------------------
def load_ground_truth(dataset: str) -> Dict[str, int]:
    """Returns {relative_file_path: label} where label 1=bug, 0=safe."""
    if dataset == "pilot":
        gt_path = PILOT_DIR / "ground_truth.json"
    else:
        gt_path = JULIET_DIR / "ground_truth.json"

    if not gt_path.exists():
        return {}

    raw = json.loads(gt_path.read_text())
    return {k: v["label"] for k, v in raw.items()}


# ---------------------------------------------------------------------------
# Final decision logic
# ---------------------------------------------------------------------------
def decide(
    triage: Optional[Dict[str, Any]],
    symexec: Optional[Dict[str, Any]],
) -> str:
    """
    Combine triage and symexec results into a final pipeline decision.

    Precedence:
      - If symexec result exists and is "feasible"   → confirmed_true
      - If symexec result exists and is "infeasible" → confirmed_false
      - If triage decision is "likely_true"           → triage_true
      - If triage decision is "likely_false"          → triage_false
      - Otherwise                                     → unresolved
    """
    if symexec:
        if symexec.get("status") == "feasible":
            return "confirmed_true"
        if symexec.get("status") == "infeasible":
            return "confirmed_false"

    if triage:
        decision = triage.get("llm_decision", "")
        if decision == "likely_true":
            return "triage_true"
        if decision == "likely_false":
            return "triage_false"

    return "unresolved"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Merge pipeline stage outputs")
    parser.add_argument("--dataset", choices=["pilot", "juliet"], default="pilot")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_FINAL_OUTPUT, help="Output file path"
    )
    args = parser.parse_args()

    # --- Load stage outputs ---
    if not DEFAULT_ANALYZER_OUTPUT.exists():
        print(f"ERROR: Analyzer output not found: {DEFAULT_ANALYZER_OUTPUT}")
        sys.exit(1)

    warnings_raw: List[Dict[str, Any]] = json.loads(DEFAULT_ANALYZER_OUTPUT.read_text())

    triage_raw: List[Dict[str, Any]] = (
        json.loads(DEFAULT_TRIAGE_OUTPUT.read_text())
        if DEFAULT_TRIAGE_OUTPUT.exists()
        else []
    )

    symexec_path = KLEE_RUNS_DIR / "symexec_results.json"
    symexec_raw: List[Dict[str, Any]] = (
        json.loads(symexec_path.read_text()) if symexec_path.exists() else []
    )

    ground_truth = load_ground_truth(args.dataset)

    # Build lookup maps
    triage_map: Dict[str, Dict[str, Any]] = {t["warning_id"]: t for t in triage_raw}
    symexec_map: Dict[str, Dict[str, Any]] = {s["warning_id"]: s for s in symexec_raw}

    # --- Merge ---
    merged: List[Dict[str, Any]] = []
    for w in warnings_raw:
        wid = w["warning_id"]
        t = triage_map.get(wid)
        s = symexec_map.get(wid)
        gt_label = ground_truth.get(w.get("file", ""), None)

        final = decide(t, s)

        # Aggregate timing (triage + symexec)
        total_time: Optional[float] = None
        triage_time = (t or {}).get("triage_time_s")
        symexec_time = (s or {}).get("klee_time_s")
        if triage_time is not None or symexec_time is not None:
            total_time = round((triage_time or 0.0) + (symexec_time or 0.0), 3)

        merged.append(
            {
                "warning_id": wid,
                "warning": w,
                "triage": t,
                "symexec": s,
                "ground_truth": gt_label,
                "final_decision": final,
                "total_pipeline_time_s": total_time,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(merged, indent=2))

    # Summary
    decisions = [r["final_decision"] for r in merged]
    print(f"=== Pipeline merge complete ({args.dataset}) ===")
    print(f"  Total warnings   : {len(merged)}")
    for val in ["confirmed_true", "confirmed_false", "triage_true", "triage_false", "unresolved"]:
        print(f"  {val:<22}: {decisions.count(val)}")
    print(f"\nWrote → {args.out}")


if __name__ == "__main__":
    main()

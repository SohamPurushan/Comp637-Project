"""
evaluate.py
~~~~~~~~~~~
Computes and prints evaluation metrics for three experimental systems:

  System 1: Analyzer-only
    A warning is flagged as a true positive if Clang emits it.
    (Every warning is treated as a positive prediction.)

  System 2: Analyzer + LLM triage
    Only warnings with llm_decision == "likely_true" are positive predictions.

  System 3: Analyzer + LLM triage + Symbolic execution  (full pipeline)
    KLEE "feasible" → confirmed true positive.
    KLEE "infeasible" → confirmed false positive.
    Remaining are resolved by triage decision, same as System 2.

Metrics reported for each system:
  TP, FP, TN, FN, Detection Accuracy, Precision, Recall, F1, FPR,
  Avg runtime per warning (s)

Usage:
    python evaluation/evaluate.py --dataset pilot
    python evaluation/evaluate.py --dataset juliet
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_FINAL_OUTPUT, RESULTS_DIR


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def safe_div(a: float, b: float) -> float:
    return a / b if b > 0 else 0.0


def compute_metrics(records: List[Dict[str, Any]], system: int) -> Dict[str, Any]:
    """
    system 1 → analyzer-only  (all warnings = positive prediction)
    system 2 → +LLM triage
    system 3 → +KLEE symexec
    """
    tp = fp = tn = fn = 0
    total_time = 0.0
    timed = 0

    for r in records:
        gt = r.get("ground_truth")
        if gt is None:
            continue  # skip records without ground truth

        t = r.get("triage") or {}
        s = r.get("symexec") or {}

        # --- determine prediction ---
        if system == 1:
            prediction = 1  # analyzer always predicts bug

        elif system == 2:
            llm_dec = t.get("llm_decision", "uncertain")
            if llm_dec == "likely_true":
                prediction = 1
            elif llm_dec == "likely_false":
                prediction = 0
            else:  # uncertain → conservative: keep as positive
                prediction = 1

        else:  # system 3
            klee_status = s.get("status")
            if klee_status == "feasible":
                prediction = 1
            elif klee_status == "infeasible":
                prediction = 0
            else:
                # Fall back to LLM decision
                llm_dec = t.get("llm_decision", "uncertain")
                if llm_dec == "likely_false":
                    prediction = 0
                else:
                    prediction = 1  # uncertain → conservative

        # --- accumulate ---
        if gt == 1 and prediction == 1:
            tp += 1
        elif gt == 0 and prediction == 1:
            fp += 1
        elif gt == 0 and prediction == 0:
            tn += 1
        elif gt == 1 and prediction == 0:
            fn += 1

        # Runtime
        rt = r.get("total_pipeline_time_s")
        if rt is not None:
            total_time += rt
            timed += 1

    total = tp + fp + tn + fn
    accuracy = safe_div(tp + tn, total)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    fpr = safe_div(fp, fp + tn)
    avg_rt = safe_div(total_time, timed) if timed else None

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "total_with_gt": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "avg_runtime_s": round(avg_rt, 3) if avg_rt is not None else "n/a",
    }


def print_table(results: Dict[str, Dict[str, Any]]) -> None:
    systems = list(results.keys())
    metrics = ["tp", "fp", "tn", "fn", "accuracy", "precision", "recall", "f1", "fpr", "avg_runtime_s"]

    col_w = 18
    header = f"{'Metric':<20}" + "".join(f"{s:>{col_w}}" for s in systems)
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for m in metrics:
        row = f"{m:<20}" + "".join(f"{str(results[s].get(m, '')):>{col_w}}" for s in systems)
        print(row)
    print("=" * len(header) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pipeline systems")
    parser.add_argument("--dataset", choices=["pilot", "juliet"], default="pilot")
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_FINAL_OUTPUT,
        help="Path to pipeline_results.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=RESULTS_DIR / "evaluation_metrics.json",
        help="Where to save metrics JSON",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Pipeline results not found: {args.input}")
        print("Run  python pipeline.py  first.")
        sys.exit(1)

    records: List[Dict[str, Any]] = json.loads(args.input.read_text())

    gt_count = sum(1 for r in records if r.get("ground_truth") is not None)
    print(f"=== Evaluation ({args.dataset}) ===")
    print(f"  Total records    : {len(records)}")
    print(f"  With ground truth: {gt_count}")

    if gt_count == 0:
        print("\nWARNING: No ground-truth labels found in pipeline_results.json.")
        print("Run  python dataset/prepare_pilot.py  (or prepare_juliet.py) to generate labels,")
        print("then re-run  python pipeline.py  before evaluating.\n")
        sys.exit(0)

    results = {
        "System 1: Analyzer-only": compute_metrics(records, 1),
        "System 2: +LLM Triage": compute_metrics(records, 2),
        "System 3: +LLM+KLEE": compute_metrics(records, 3),
    }

    print_table(results)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"Metrics saved → {args.out}")


if __name__ == "__main__":
    main()

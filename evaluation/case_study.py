"""
case_study.py
~~~~~~~~~~~~~
Prints a full worked end-to-end example of one warning flowing through
all three pipeline stages:

  Clang Static Analyzer warning
       ↓
  Qwen2.5-Coder-7B-Instruct triage output
       ↓
  KLEE symbolic-execution result
       ↓
  Final pipeline decision

By default it picks the first warning whose full pipeline trace exists
(has triage + symexec results). Pass --warning-id W... to choose a specific
warning.

Usage:
    python evaluation/case_study.py
    python evaluation/case_study.py --warning-id W0000
    python evaluation/case_study.py --out results/case_study.txt
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_FINAL_OUTPUT


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
SEP = "─" * 72


def _head(title: str) -> str:
    return f"\n{SEP}\n  {title}\n{SEP}"


def _field(label: str, value: Any, indent: int = 2) -> str:
    pad = " " * indent
    if isinstance(value, list):
        if not value:
            return f"{pad}{label}: (none)"
        items = "\n".join(f"{pad}    • {v}" for v in value)
        return f"{pad}{label}:\n{items}"
    return f"{pad}{label}: {value}"


def format_record(record: Dict[str, Any]) -> str:
    lines = []

    # ------------------------------------------------------------------ #
    # Stage 1 – Static analysis warning                                   #
    # ------------------------------------------------------------------ #
    lines.append(_head("STAGE 1 — Clang Static Analyzer"))
    w = record.get("warning") or {}
    lines.append(_field("Warning ID", record.get("warning_id", "?")))
    lines.append(_field("File", w.get("file", "?")))
    lines.append(_field("Line", w.get("line", "?")))
    lines.append(_field("Checker", w.get("checker", "?")))
    lines.append(_field("Message", w.get("message", "?")))

    ctx = w.get("code_context", [])
    if ctx:
        lines.append("\n  Code context:")
        for cl in ctx:
            lines.append(f"      {cl}")

    # ------------------------------------------------------------------ #
    # Stage 2 – LLM triage                                                #
    # ------------------------------------------------------------------ #
    lines.append(_head("STAGE 2 — Qwen2.5-Coder-7B-Instruct Triage"))
    t = record.get("triage") or {}
    if not t:
        lines.append("  (no triage result — run python llm_triage/triage.py)")
    else:
        lines.append(_field("Decision", t.get("llm_decision", "?")))
        lines.append(_field("Confidence", t.get("confidence", "?")))
        lines.append(_field("Predicted bug type", t.get("predicted_bug_type", "?")))
        lines.append(_field("Reasoning", t.get("reasoning", "?")))
        lines.append(_field("Relevant variables", t.get("relevant_variables", [])))
        lines.append(_field("Branch conditions", t.get("branch_conditions", [])))
        lines.append(_field("Suspicious locations", t.get("suspicious_locations", [])))
        if t.get("triage_time_s") is not None:
            lines.append(_field("Triage time", f"{t['triage_time_s']} s"))

    # ------------------------------------------------------------------ #
    # Stage 3 – KLEE symbolic execution                                   #
    # ------------------------------------------------------------------ #
    lines.append(_head("STAGE 3 — KLEE Symbolic Execution"))
    s = record.get("symexec") or {}
    if not s:
        lines.append("  (no symexec result — run python symexec/verify_klee.py)")
    else:
        lines.append(_field("KLEE status", s.get("status", "?")))
        lines.append(_field("Details", s.get("details", "?")))
        lines.append(_field("Target file", s.get("target_file", "?")))
        lines.append(_field("Target line", s.get("target_line", "?")))
        lines.append(_field("Focus variables", s.get("focus_variables", [])))
        lines.append(_field("Focus conditions", s.get("focus_conditions", [])))

    # ------------------------------------------------------------------ #
    # Final decision                                                       #
    # ------------------------------------------------------------------ #
    lines.append(_head("FINAL PIPELINE DECISION"))
    gt = record.get("ground_truth")
    final = record.get("final_decision", "unresolved")
    lines.append(_field("Decision", final))
    if gt is not None:
        gt_str = "BUG (1)" if gt == 1 else "SAFE (0)"
        lines.append(_field("Ground truth", gt_str))
        correct = (
            (final in {"confirmed_true", "triage_true"} and gt == 1)
            or (final in {"confirmed_false", "triage_false"} and gt == 0)
        )
        lines.append(_field("Correct?", "✓ YES" if correct else "✗ NO"))
    else:
        lines.append(_field("Ground truth", "(not available)"))

    lines.append(f"\n{SEP}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def pick_record(
    records: list,
    warning_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    if warning_id:
        for r in records:
            if r.get("warning_id") == warning_id:
                return r
        print(f"WARNING: warning_id '{warning_id}' not found in pipeline results.")
        return None

    # Prefer a record with both triage and symexec filled in
    for r in records:
        if r.get("triage") and r.get("symexec"):
            return r

    # Fall back to any record with triage
    for r in records:
        if r.get("triage"):
            return r

    # Last resort: first record
    return records[0] if records else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Print end-to-end pipeline case study")
    parser.add_argument("--input", type=Path, default=DEFAULT_FINAL_OUTPUT)
    parser.add_argument("--warning-id", type=str, default=None, dest="warning_id")
    parser.add_argument("--out", type=Path, default=None, help="Optional file to write output to")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Pipeline results not found: {args.input}")
        print("Run  python pipeline.py  first.")
        sys.exit(1)

    records = json.loads(args.input.read_text())
    if not records:
        print("No records in pipeline_results.json.")
        sys.exit(0)

    record = pick_record(records, args.warning_id)
    if record is None:
        print("Could not find a suitable record.")
        sys.exit(1)

    output = format_record(record)
    print(output)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output)
        print(f"Case study saved → {args.out}")


if __name__ == "__main__":
    main()

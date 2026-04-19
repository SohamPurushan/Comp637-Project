"""
Pipeline script that merges analyzer warnings, LLM triage, and KLEE symbolic execution results.
"""

import json
from pathlib import Path

from config import DEFAULT_ANALYZER_OUTPUT, DEFAULT_FINAL_OUTPUT, DEFAULT_TRIAGE_OUTPUT, KLEE_RUNS_DIR
from schemas import LLMTriageRecord, WarningRecord


def main() -> None:
    warnings = [WarningRecord(**x) for x in json.loads(Path(DEFAULT_ANALYZER_OUTPUT).read_text())]
    triage = [LLMTriageRecord(**x) for x in json.loads(Path(DEFAULT_TRIAGE_OUTPUT).read_text())]

    symexec_path = KLEE_RUNS_DIR / "symexec_results.json"
    symexec = json.loads(symexec_path.read_text()) if symexec_path.exists() else []

    triage_map = {t.warning_id: t.model_dump() for t in triage}
    symexec_map = {s["warning_id"]: s for s in symexec}

    merged = []
    for w in warnings:
        merged.append(
            {
                "warning": w.model_dump(),
                "triage": triage_map.get(w.warning_id),
                "symexec": symexec_map.get(w.warning_id),
            }
        )

    DEFAULT_FINAL_OUTPUT.write_text(json.dumps(merged, indent=2))
    print(f"Wrote merged pipeline output to {DEFAULT_FINAL_OUTPUT}")


if __name__ == "__main__":
    main()

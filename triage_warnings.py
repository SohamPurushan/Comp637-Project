import json
import re
import argparse
from pathlib import Path
from typing import List

from config import TARGET_BUG_CLASS
from schemas import LLMTriageRecord, WarningRecord


parser = argparse.ArgumentParser(description="Triage Clang static analyzer warnings.")
parser.add_argument(
    "--input",
    default="results/clang_warnings.json",
    help="Path to analyzer warning JSON file.",
)
parser.add_argument(
    "--output",
    default="results/triaged_warnings.json",
    help="Path to write triage output JSON file.",
)
args = parser.parse_args()

INPUT_FILE = Path(args.input)
OUTPUT_FILE = Path(args.output)


def load_warnings() -> List[WarningRecord]:
    warning_path = INPUT_FILE

    if not warning_path.exists():
        raise FileNotFoundError(
            f"Analyzer output not found: {warning_path}. Run run_clang.py first."
        )

    raw = json.loads(warning_path.read_text())
    return [WarningRecord(**item) for item in raw]


def extract_context(source_file: str, warning_line: int, radius: int = 5) -> str:
    path = Path(source_file)
    if not path.exists():
        return ""

    lines = path.read_text(errors="replace").splitlines()

    start = max(0, warning_line - 1 - radius)
    end = min(len(lines), warning_line - 1 + radius + 1)

    selected = [(i + 1, lines[i]) for i in range(start, end)]

    while selected and selected[0][1].strip() == "":
        selected.pop(0)
    while selected and selected[-1][1].strip() == "":
        selected.pop()

    return "\n".join(f"{line_no}: {text}" for line_no, text in selected)


def build_prompt(warning: WarningRecord, context: str) -> str:
    return f"""
You are analyzing a static-analysis warning for a C/C++ program.

Task:
Decide whether this warning is likely a real bug, likely a false positive, or uncertain.

Return your answer as valid JSON with exactly these fields:
- warning_id (string)
- llm_decision (string: "likely_true", "likely_false", or "uncertain")
- confidence (number from 0.0 to 1.0)
- predicted_bug_type (string or null)
- reasoning (string)
- relevant_variables (array of strings)
- branch_conditions (array of strings)

Warning:
- warning_id: {warning.warning_id}
- file: {warning.file}
- line: {warning.line}
- column: {warning.column}
- message: {warning.message}
- checker: {warning.checker}
- category: {warning.category}

Code context:
{context}
""".strip()


def extract_pointer_names(context: str) -> List[str]:
    names = set()

    decl_pattern = re.compile(r"\*\s*([A-Za-z_][A-Za-z0-9_]*)")
    for match in decl_pattern.finditer(context):
        names.add(match.group(1))

    deref_pattern = re.compile(r"\*([A-Za-z_][A-Za-z0-9_]*)")
    for match in deref_pattern.finditer(context):
        names.add(match.group(1))

    return sorted(names)


def extract_branch_conditions(context: str) -> List[str]:
    conditions = []

    if_pattern = re.compile(r"\bif\s*\((.*?)\)")
    while_pattern = re.compile(r"\bwhile\s*\((.*?)\)")

    for match in if_pattern.finditer(context):
        conditions.append(match.group(1).strip())

    for match in while_pattern.finditer(context):
        conditions.append(match.group(1).strip())

    return conditions


def mock_llm_triage(warning: WarningRecord, context: str) -> LLMTriageRecord:
    relevant_variables = extract_pointer_names(context)
    branch_conditions = extract_branch_conditions(context)

    checker = warning.checker.lower()
    message = warning.message.lower()
    context_lower = context.lower()

    if "nulldereference" in checker or "null pointer" in message:
        if "!= null" in context_lower or "!= 0" in context_lower:
            decision = "uncertain"
            confidence = 0.75
            reasoning = (
                "The warning involves a null dereference pattern, but the nearby context "
                "includes a null check or guard, so feasibility is uncertain from this local context."
            )
        else:
            decision = "likely_true"
            confidence = 0.95
            reasoning = (
                "The warning indicates a null-pointer dereference and the nearby context "
                "does not show a protective guard before the dereference."
            )
        predicted_bug_type = TARGET_BUG_CLASS
    else:
        decision = "uncertain"
        confidence = 0.50
        predicted_bug_type = None
        reasoning = (
            "The mock triage logic does not have a specific rule for this checker, "
            "so the result remains uncertain."
        )

    return LLMTriageRecord(
        warning_id=warning.warning_id,
        llm_decision=decision,
        confidence=confidence,
        predicted_bug_type=predicted_bug_type,
        reasoning=reasoning,
        relevant_variables=relevant_variables,
        branch_conditions=branch_conditions,
    )


def main() -> None:
    warnings = load_warnings()
    triage_results: List[LLMTriageRecord] = []

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not warnings:
        OUTPUT_FILE.write_text("[]")
        print(f"No warnings found in {INPUT_FILE}")
        print(f"Wrote empty triage output to {OUTPUT_FILE}")
        return

    for warning in warnings:
        context = extract_context(warning.file, warning.line, radius=5)
        prompt = build_prompt(warning, context)

        print(f"\n=== TRIAGING {warning.warning_id} ===")
        print("Prompt preview:")
        print(prompt)
        print()

        triage_record = mock_llm_triage(warning, context)
        triage_results.append(triage_record)

    OUTPUT_FILE.write_text(
        json.dumps([record.model_dump() for record in triage_results], indent=2)
    )

    print(f"Wrote {len(triage_results)} triage record(s) to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
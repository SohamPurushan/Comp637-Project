import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    CLANG_BIN,
    DEFAULT_ANALYZER_OUTPUT,
    DEFAULT_TRIAGE_OUTPUT,
    KLEE_BIN,
    KLEE_INCLUDE_DIR,
    KLEE_MAX_TIME,
    KLEE_RUNS_DIR,
    TARGETS_MANIFEST,
)
from schemas import LLMTriageRecord, SymExecTask, WarningRecord


def load_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text())


def load_warnings() -> List[WarningRecord]:
    raw = load_json(DEFAULT_ANALYZER_OUTPUT)
    return [WarningRecord(**x) for x in raw]


def load_triage() -> List[LLMTriageRecord]:
    raw = load_json(DEFAULT_TRIAGE_OUTPUT)
    return [LLMTriageRecord(**x) for x in raw]


def load_targets() -> Dict[str, dict]:
    if not TARGETS_MANIFEST.exists():
        raise FileNotFoundError(
            f"Missing targets manifest: {TARGETS_MANIFEST}. Create it before running symexec."
        )
    raw = json.loads(TARGETS_MANIFEST.read_text())
    return {entry["source_file"]: entry for entry in raw}


def build_tasks(
    warnings: List[WarningRecord],
    triage: List[LLMTriageRecord],
    targets: Dict[str, dict],
) -> List[SymExecTask]:
    triage_map = {t.warning_id: t for t in triage}
    tasks: List[SymExecTask] = []

    for warning in warnings:
        t = triage_map.get(warning.warning_id)
        if t is None:
            continue

        # First version: only verify warnings the triage stage thinks are real or uncertain
        if t.llm_decision not in {"likely_true", "uncertain"}:
            continue

        source_name = Path(warning.file).name
        target = targets.get(source_name)
        if not target:
            continue

        tasks.append(
            SymExecTask(
                warning_id=warning.warning_id,
                target_file=target["target_file"],
                target_line=target.get("target_line", warning.line),
                expected_bug_type=t.predicted_bug_type or "UNKNOWN",
                focus_variables=t.relevant_variables,
                focus_conditions=t.branch_conditions,
            )
        )

    return tasks


def compile_to_bc(task: SymExecTask, workdir: Path) -> Path:
    source_path = Path(task.target_file)
    if not source_path.exists():
        raise FileNotFoundError(f"Target file not found: {source_path}")

    bc_path = workdir / f"{source_path.stem}.bc"

    cmd = [
        CLANG_BIN,
        "-I",
        KLEE_INCLUDE_DIR,
        "-emit-llvm",
        "-c",
        "-g",
        "-O0",
        "-Xclang",
        "-disable-O0-optnone",
        str(source_path),
        "-o",
        str(bc_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"LLVM bitcode compilation failed for {source_path}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    return bc_path


def run_klee_on_bc(bc_path: Path, out_dir: Path) -> subprocess.CompletedProcess:
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        KLEE_BIN,
        "--output-dir",
        str(out_dir),
        "--max-time",
        KLEE_MAX_TIME,
        str(bc_path),
    ]

    return subprocess.run(cmd, capture_output=True, text=True)


def classify_klee_result(proc: subprocess.CompletedProcess) -> tuple[str, str]:
    combined = "\n".join([proc.stdout.strip(), proc.stderr.strip()]).strip().lower()

    # First-pass heuristic classification
    if "halt timer invoked" in combined or "timed out" in combined:
        return "timeout", combined

    if "error:" in combined or "memory error" in combined or "null pointer exception" in combined:
        return "feasible", combined

    if proc.returncode == 0:
        return "infeasible", combined if combined else "KLEE completed without reporting an error path."

    return "timeout", combined if combined else "KLEE failed without a classified result."


def verify_task(task: SymExecTask) -> dict:
    task_dir = KLEE_RUNS_DIR / task.warning_id
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        bc_path = compile_to_bc(task, task_dir)
        proc = run_klee_on_bc(bc_path, task_dir / "klee-out")
        status, details = classify_klee_result(proc)

        return {
            "warning_id": task.warning_id,
            "status": status,   # feasible / infeasible / timeout
            "details": details,
            "target_file": task.target_file,
            "target_line": task.target_line,
            "expected_bug_type": task.expected_bug_type,
            "focus_variables": task.focus_variables,
            "focus_conditions": task.focus_conditions,
        }
    except Exception as e:
        return {
            "warning_id": task.warning_id,
            "status": "timeout",
            "details": f"Symexec stage failed: {e}",
            "target_file": task.target_file,
            "target_line": task.target_line,
            "expected_bug_type": task.expected_bug_type,
            "focus_variables": task.focus_variables,
            "focus_conditions": task.focus_conditions,
        }


def main() -> None:
    warnings = load_warnings()
    triage = load_triage()
    targets = load_targets()

    tasks = build_tasks(warnings, triage, targets)
    if not tasks:
        out_path = KLEE_RUNS_DIR / "symexec_results.json"
        out_path.write_text("[]")
        print(f"No symbolic-execution tasks generated. Wrote empty file to {out_path}")
        return

    results = []
    for task in tasks:
        print(f"=== VERIFYING {task.warning_id} ===")
        print(f"Target file: {task.target_file}")
        results.append(verify_task(task))

    out_path = KLEE_RUNS_DIR / "symexec_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {len(results)} symexec result(s) to {out_path}")


if __name__ == "__main__":
    main()
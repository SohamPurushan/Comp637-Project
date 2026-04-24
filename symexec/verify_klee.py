import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# Make repo-root imports work when running:
#   python3 symexec/verify_klee.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

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
    cleaned = []
    for x in raw:
        cleaned.append(
            WarningRecord(
                warning_id=x["warning_id"],
                file=x["file"],
                line=x["line"],
                column=x["column"],
                message=x["message"],
                checker=x["checker"],
                category=x.get("category", ""),
                code_context=x.get("code_context", []),
            )
        )
    return cleaned


def load_triage() -> List[LLMTriageRecord]:
    raw = load_json(DEFAULT_TRIAGE_OUTPUT)
    cleaned = []
    for x in raw:
        cleaned.append(
            LLMTriageRecord(
                warning_id=x["warning_id"],
                llm_decision=x["llm_decision"],
                confidence=x.get("confidence", 0.0),
                predicted_bug_type=x.get("predicted_bug_type", "UNKNOWN"),
                reasoning=x.get("reasoning", ""),
                relevant_variables=x.get("relevant_variables", []),
                branch_conditions=x.get("branch_conditions", []),
                suspicious_locations=x.get("suspicious_locations", []),
            )
        )
    return cleaned


def load_targets() -> Dict[str, dict]:
    if not TARGETS_MANIFEST.exists():
        raise FileNotFoundError(
            f"Missing targets manifest: {TARGETS_MANIFEST}. "
            "Run python3 symexec/generate_targets.py first."
        )

    raw = json.loads(TARGETS_MANIFEST.read_text())
    out = {}

    for entry in raw:
        sf = entry["source_file"]
        p = Path(sf)

        # absolute path
        out[str(p)] = entry

        # repo-relative if possible
        try:
            rel = str(p.relative_to(PROJECT_ROOT))
            out[rel] = entry
        except Exception:
            pass

        # basename fallback
        out[p.name] = entry

    return out


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

        # Only verify warnings that survive triage.
        if t.llm_decision not in {"likely_true", "uncertain"}:
            continue

        target = (
            targets.get(warning.file)
            or targets.get(str(PROJECT_ROOT / warning.file))
            or targets.get(Path(warning.file).name)
        )
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
    source_path = Path(task.target_file).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Target file not found: {source_path}")

    bc_path = workdir / f"{source_path.stem}.bc"

    source_dir = source_path.parent
    source_name = source_path.name
    bc_name = bc_path.name

    cmd = [
        "docker", "run", "--rm",
        "--platform", "linux/amd64",
        "-v", f"{source_dir}:/src",
        "-v", f"{workdir.resolve()}:/out",
        "-w", "/src",
        "klee/klee:3.1",
        "clang",
        "-I", "/home/klee/klee/include",
        "-emit-llvm",
        "-c",
        "-g",
        "-O0",
        "-Xclang", "-disable-O0-optnone",
        source_name,
        "-o", f"/out/{bc_name}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"LLVM bitcode compilation failed for {source_path}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    if not bc_path.exists():
        raise RuntimeError(f"Bitcode file was not created: {bc_path}")

    return bc_path


def run_klee_on_bc(bc_path: Path, out_dir: Path) -> subprocess.CompletedProcess:
    task_dir = bc_path.parent.resolve()
    bc_name = bc_path.name

    # Remove any old KLEE output so KLEE can create a fresh directory
    if out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)

    cmd = [
        "docker", "run", "--rm",
        "--platform", "linux/amd64",
        "-v", f"{task_dir}:/work",
        "-w", "/work",
        "klee/klee:3.1",
        "klee",
        "--output-dir=/work/klee-out",
        f"--max-time={KLEE_MAX_TIME}",
        f"/work/{bc_name}",
    ]
    return subprocess.run(cmd, capture_output=True, text=True)

def classify_klee_result(proc: subprocess.CompletedProcess) -> tuple[str, str]:
    combined = "\n".join([proc.stdout.strip(), proc.stderr.strip()]).strip().lower()

    # Genuine timeout
    if "halt timer invoked" in combined or "timed out" in combined:
        return "timeout", combined

    # Infrastructure / execution failures
    if "failed: no such file or directory" in combined:
        return "timeout", combined
    if "unable to load" in combined or "loading file" in combined:
        return "timeout", combined
    if "docker:" in combined and "not found" in combined:
        return "timeout", combined

    # Actual bug-triggering style outcomes
    if "memory error" in combined or "null pointer exception" in combined:
        return "feasible", combined

    # Clean completion with no reported error path
    if proc.returncode == 0:
        return (
            "infeasible",
            combined if combined else "KLEE completed without reporting an error path.",
        )

    # Everything else is unresolved failure
    return (
        "timeout",
        combined if combined else "KLEE failed without a classified result.",
    )

def verify_task(task: SymExecTask) -> dict:
    task_dir = KLEE_RUNS_DIR / task.warning_id
    task_dir.mkdir(parents=True, exist_ok=True)

    try:
        bc_path = compile_to_bc(task, task_dir)
        if not bc_path.exists():
            raise RuntimeError(f"Bitcode file was not created: {bc_path}")
        proc = run_klee_on_bc(bc_path, task_dir / "klee-out")
        status, details = classify_klee_result(proc)
        return {
            "warning_id": task.warning_id,
            "status": status,
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

    out_path = KLEE_RUNS_DIR / "symexec_results.json"

    if not tasks:
        out_path.write_text("[]")
        print(f"No symbolic-execution tasks generated. Wrote empty file to {out_path}")
        return

    results = []
    for task in tasks:
        print(f"=== VERIFYING {task.warning_id} ===")
        print(f"Target file: {task.target_file}")
        results.append(verify_task(task))

    out_path.write_text(json.dumps(results, indent=2))
    print(f"Wrote {len(results)} symexec result(s) to {out_path}")


if __name__ == "__main__":
    main()
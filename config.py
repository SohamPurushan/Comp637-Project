from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
PILOT_DIR = DATA_DIR / "pilot"
JULIET_DIR = DATA_DIR / "juliet"
RESULTS_DIR = PROJECT_ROOT / "results"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

QWEN_MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"

TARGET_BUG_CLASS = "CWE-476"
TARGET_BUG_NAME = "null pointer dereference"

DEFAULT_SOURCE_DIR = PILOT_DIR
DEFAULT_ANALYZER_OUTPUT = RESULTS_DIR / "clang_warnings.json"
DEFAULT_TRIAGE_OUTPUT = RESULTS_DIR / "triaged_warnings.json"
DEFAULT_FINAL_OUTPUT = RESULTS_DIR / "pipeline_results.json"

# --- KLEE / LLVM toolchain ---
# Using Homebrew LLVM (installed at /opt/homebrew/opt/llvm)
CLANG_BIN = "/usr/bin/clang"
LLVM_LINK_BIN = "/opt/homebrew/opt/llvm/bin/llvm-link"

# KLEE via Docker (start Docker Desktop first, then run: docker pull klee/klee:3.1)
# The wrapper script will handle running KLEE inside Docker
KLEE_BIN = str(PROJECT_ROOT / "scripts" / "klee-docker.sh")

# KLEE include directory (inside Docker container, mapped via wrapper script)
KLEE_INCLUDE_DIR = str(PROJECT_ROOT / "klee_include")

KLEE_MAX_TIME = "30s"
KLEE_RUNS_DIR = RESULTS_DIR / "klee_runs"
KLEE_RUNS_DIR.mkdir(parents=True, exist_ok=True)

# Manifest that describes which target functions can be exercised
TARGETS_MANIFEST = PROJECT_ROOT / "symexec" / "targets.json"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
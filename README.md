# Hybrid Static Analysis Pipeline for CWE-476 (Null Pointer Dereference)

A three-stage hybrid vulnerability detection pipeline for C/C++ programs:

1. **Clang Static Analyzer** — generates candidate warnings
2. **Qwen2.5-Coder-7B-Instruct** (LLM) — triages each warning with structured output
3. **KLEE** (symbolic execution) — confirms or refutes feasibility of flagged paths

---

## Project structure

```
.
├── config.py                        # All paths and tool configuration
├── schemas.py                       # Shared dataclass schemas
├── pipeline.py                      # Merge all stage outputs → pipeline_results.json
│
├── dataset/
│   ├── prepare_pilot.py             # Download & prepare SARD Secure/Vulnerable v2
│   └── prepare_juliet.py            # Download & filter Juliet CWE-476
│
├── analyzer/
│   └── run_clang_analyzer.py        # Stage 1: run Clang, extract warnings + code context
│
├── prompts/
│   └── triage_prompt.txt            # Structured prompt template for LLM triage
│
├── llm_triage/
│   └── triage.py                    # Stage 2: Qwen2.5-Coder triage → triaged_warnings.json
│
├── symexec/
│   ├── targets.json                 # Per-warning target specs (auto-generated or hand-edited)
│   ├── generate_targets.py          # Auto-generate targets.json from triage output
│   └── verify_klee.py               # Stage 3: compile → llvm-link → KLEE → classify
│
├── evaluation/
│   ├── evaluate.py                  # Compute TP/FP/FN/TN, accuracy, FPR, F1 for 3 systems
│   └── case_study.py                # Print one full worked example through all stages
│
├── data/
│   ├── pilot/                       # SARD Secure v2 + Vulnerable v2 + ground_truth.json
│   │   ├── secure/
│   │   ├── vulnerable/
│   │   └── ground_truth.json
│   └── juliet/                      # Filtered Juliet CWE-476 + ground_truth.json
│
└── results/
    ├── clang_warnings.json
    ├── triaged_warnings.json
    ├── klee_runs/
    │   └── symexec_results.json
    ├── pipeline_results.json
    └── evaluation_metrics.json
```

---

## Prerequisites

### Python
```bash
pip install transformers torch accelerate
```

### Clang Static Analyzer
```bash
brew install llvm          # macOS (Homebrew)
# Adds clang, llvm-link to /opt/homebrew/opt/llvm/bin/
```

### KLEE (via Docker — recommended for macOS)
```bash
# Start Docker Desktop, then:
docker pull klee/klee:3.1
```
The wrapper script `scripts/klee-docker.sh` maps your workspace into the container automatically.

---

## Full run order

### 1. Prepare datasets
```bash
python dataset/prepare_pilot.py     # downloads SARD pilot (~30 MB)
python dataset/prepare_juliet.py    # downloads Juliet 1.3.1 (~300 MB)
```

### 2. Run Clang Static Analyzer
```bash
python analyzer/run_clang_analyzer.py --dataset pilot
# or
python analyzer/run_clang_analyzer.py --dataset juliet
```
Output: `results/clang_warnings.json`

### 3. LLM triage
```bash
python llm_triage/triage.py --dataset pilot
# or with a small test limit:
python llm_triage/triage.py --dataset pilot --limit 10
```
Output: `results/triaged_warnings.json`

### 4. Generate KLEE targets
```bash
python symexec/generate_targets.py
```
Output: `symexec/targets.json`

### 5. Run KLEE symbolic execution
```bash
python symexec/verify_klee.py
```
Output: `results/klee_runs/symexec_results.json`

### 6. Merge pipeline outputs
```bash
python pipeline.py --dataset pilot
```
Output: `results/pipeline_results.json`

### 7. Evaluate (three-system comparison)
```bash
python evaluation/evaluate.py --dataset pilot
```
Output: table printed to stdout + `results/evaluation_metrics.json`

### 8. Case study
```bash
python evaluation/case_study.py
# or for a specific warning:
python evaluation/case_study.py --warning-id W0000
```

---

## Experimental systems compared

| System | Description |
|--------|-------------|
| System 1 | Analyzer-only (all Clang warnings = positive) |
| System 2 | Analyzer + LLM triage (Qwen2.5-Coder-7B-Instruct) |
| System 3 | Analyzer + LLM + KLEE symbolic execution (full pipeline) |

## Metrics

- **Detection Accuracy** — (TP + TN) / total
- **Precision** — TP / (TP + FP)
- **Recall** — TP / (TP + FN)
- **F1 Score** — harmonic mean of precision and recall
- **False Positive Rate (FPR)** — FP / (FP + TN)
- **Avg runtime per warning** (seconds)

---

## Target bug class

CWE-476: Null Pointer Dereference (C/C++)

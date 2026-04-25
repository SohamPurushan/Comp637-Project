# Experiment Results

## Overview

We evaluated three configurations of the pipeline:

1. **Analyzer-only**
2. **Analyzer + LLM Triage**
3. **Analyzer + LLM + Symbolic Execution**

The evaluation was run on two datasets:

- **Pilot dataset**: a small hand-curated null-pointer-dereference pilot set used to validate end-to-end integration and early false-positive reduction.
- **Juliet small subset**: a 10-warning subset drawn from Juliet CWE-476 cases, used as a benchmark-style end-to-end smoke test after the full pipeline was working.

## Role of Each Dataset

### Pilot dataset
The pilot dataset is the more informative comparison set in the current stage of the project. It contains both positive and negative outcomes, so it is useful for observing how LLM triage affects false positives.

### Juliet small subset
The Juliet small subset is primarily a **pipeline demonstration set**. In the current experiment, it contains only positive null-pointer-dereference cases. As a result, it is useful for showing that the analyzer, LLM triage, target generation, symbolic execution, merge stage, and evaluation all run end to end on benchmark-derived cases. However, because the subset is not balanced, its perfect scores should not be interpreted as strong evidence of discrimination between true and false warnings.

## Dataset Sizes

### Pilot
- Analyzer warnings with ground truth used in final evaluation: **5**
- Systems compared: **3**
- Included at least one false positive in the analyzer-only baseline

### Juliet small subset
- Analyzer warnings found on broader Juliet extraction: **216**
- Small subset selected for current experiment: **10**
- Records with ground truth in final evaluation: **10**
- All 10 selected warnings were positive CWE-476 cases

## Final Comparison Table

| Dataset | System | TP | FP | TN | FN | Accuracy | Precision | Recall | F1 | FPR | Avg runtime (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Pilot | Analyzer-only | 4 | 1 | 0 | 0 | 0.8000 | 0.8000 | 1.0000 | 0.8889 | 1.0000 | 962.716 |
| Pilot | Analyzer + LLM | 4 | 0 | 1 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 962.716 |
| Pilot | Analyzer + LLM + KLEE | 4 | 0 | 1 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 962.716 |
| Juliet small subset | Analyzer-only | 10 | 0 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1254.695 |
| Juliet small subset | Analyzer + LLM | 10 | 0 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1254.695 |
| Juliet small subset | Analyzer + LLM + KLEE | 10 | 0 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 1254.695 |

## Key Takeaways

### Pilot
The pilot results show that the analyzer-only baseline produced one false positive, while the LLM-based triage stage removed that false positive. On this pilot set, adding symbolic execution did not further change the final top-line metrics, but it provided confirmation support for selected cases.

### Juliet small subset
The Juliet small-subset results show that the full pipeline can run end to end on benchmark-derived CWE-476 cases. However, because all selected warnings were positive cases, the current Juliet results mainly serve as a correctness and integration demonstration rather than a balanced performance comparison.

## Runtime Notes

Runtime was dominated by local LLM inference. On the available hardware, Qwen2.5-Coder-7B-Instruct incurred substantial latency per warning, making the full pipeline slow in practice even though it was functionally correct. This runtime cost is an important practical limitation of the current prototype.

## Limitations

The current evaluation has several important limitations:

1. **Small pilot size.** The pilot experiment is useful for debugging and sanity checking, but it is too small to support strong general conclusions.
2. **Juliet subset is not balanced.** The current Juliet subset contains only positive CWE-476 cases, so it does not test false-positive behavior in a meaningful way.
3. **LLM runtime is high.** Local inference with a 7B code model is slow on the available machine, which limits scalability.
4. **Symbolic execution coverage is still limited.** Although symbolic execution is now integrated and operational, broader coverage and larger-scale evaluation remain future work.
5. **Current results are preliminary.** These experiments demonstrate feasibility and early promise, but not yet a full benchmark-scale evaluation.

## Suggested Interpretation in the Paper

A fair summary is:

> The pilot experiment provides initial evidence that LLM triage can reduce false positives relative to analyzer-only warnings. The Juliet small-subset experiment demonstrates that the full hybrid pipeline can run end to end on benchmark-derived CWE-476 cases. However, the current Juliet subset is not balanced, so larger or more diverse benchmark slices are needed for stronger empirical conclusions.

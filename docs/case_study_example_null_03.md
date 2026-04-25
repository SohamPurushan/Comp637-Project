# Case Study: Confirmed Null-Pointer Dereference in `example_null_03.c`

## Source File

**File:** `data/pilot/example_null_03.c`

```c
#include <stdio.h>

int main() {
    int *p = NULL;
    return *p;
}
```

This example initializes pointer `p` to `NULL` and then immediately dereferences it on line 5.

## 1. Static Analyzer Warning

The Clang Static Analyzer reported warning **`W9552F0E`** with:

- **Checker:** `core.NullDereference`
- **Category:** `Logic error`
- **Message:** `Dereference of null pointer (loaded from variable 'p')`
- **Location:** line 5, column 12

Extracted code context:

```text
1 #include <stdio.h>
2 
3 int main() {
4     int *p = NULL;
5     return *p;
6 }
```

## 2. LLM Triage Result

The LLM triage stage classified the warning as:

- **Decision:** `likely_true`
- **Confidence:** `0.9`
- **Predicted bug type:** `CWE-476`

Structured reasoning output:

- **Relevant variable:** `p`
- **Branch condition:** `p == NULL`

Reasoning summary:

> The dereference of the null pointer `p` on line 5 will definitely lead to a segmentation fault.

## 3. Target Generation

The symbolic-execution target-generation stage mapped the warning to the following verification target:

- **Function:** `main`
- **Return type:** `int`
- **Arguments:** none
- **Target line:** `5`

This created a direct verification task for the enclosing function.

## 4. Symbolic Execution Result

KLEE verified the case as **feasible**.

Important output excerpt:

```text
klee: error: example_null_03.c:5: memory error: null page access
klee: note: now ignoring this error at this location
klee: done: generated tests = 1
```

This confirms that the reported null dereference corresponds to an executable bad path.

## 5. Final Pipeline Decision

The merged pipeline output classified this warning as:

- **Final decision:** `confirmed_true`

So the full flow for this case was:

1. Static analyzer reported a null-dereference warning.
2. LLM triage kept the warning and identified the key variable and condition.
3. Target generation mapped the warning to `main` at line 5.
4. KLEE confirmed a feasible null page access.
5. The pipeline marked the warning as a confirmed true vulnerability.

## Why This Case Is Useful

This is a strong illustrative example because all three stages agree:

- the analyzer detects the vulnerability,
- the LLM triage correctly judges it as likely real,
- and symbolic execution confirms it with a concrete memory error.

As a result, this case clearly demonstrates the intended role of the hybrid design: semantic narrowing by the LLM followed by stronger path-feasibility confirmation through symbolic execution.

"""
triage.py
~~~~~~~~~
LLM triage stage: reads clang_warnings.json, sends each warning + code context
to Qwen2.5-Coder-7B-Instruct, parses structured JSON output, and writes
results/triaged_warnings.json.

Each output record extends the input WarningRecord with the fields produced
by the model:
  llm_decision, confidence, predicted_bug_type, reasoning,
  relevant_variables, branch_conditions, suspicious_locations

Usage:
    python llm_triage/triage.py --dataset pilot
    python llm_triage/triage.py --dataset juliet [--limit 100]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    DEFAULT_ANALYZER_OUTPUT,
    DEFAULT_TRIAGE_OUTPUT,
    PROMPTS_DIR,
    QWEN_MODEL_NAME,
    RESULTS_DIR,
)

# ---------------------------------------------------------------------------
# Lazy model loading (only imported when needed so the script can be imported
# for testing without requiring GPU/transformers)
# ---------------------------------------------------------------------------
_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("ERROR: transformers and torch are required.\n"
              "Install with:  pip install transformers torch accelerate")
        sys.exit(1)

    print(f"Loading {QWEN_MODEL_NAME} …")
    _tokenizer = AutoTokenizer.from_pretrained(
        QWEN_MODEL_NAME, trust_remote_code=True
    )
    _model = AutoModelForCausalLM.from_pretrained(
        QWEN_MODEL_NAME,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    _model.eval()
    print("Model loaded.\n")
    return _model, _tokenizer


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE_PATH = PROMPTS_DIR / "triage_prompt.txt"


def load_prompt_template() -> str:
    if not PROMPT_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Prompt template not found: {PROMPT_TEMPLATE_PATH}")
    return PROMPT_TEMPLATE_PATH.read_text()


def build_prompt(warning: Dict[str, Any], template: str) -> str:
    code_ctx = "\n".join(warning.get("code_context", []))
    return template.format(
        file=warning.get("file", "unknown"),
        line=warning.get("line", "?"),
        checker=warning.get("checker", "unknown"),
        message=warning.get("message", ""),
        code_context=code_ctx,
    )


# ---------------------------------------------------------------------------
# Model inference
# ---------------------------------------------------------------------------
def query_model(prompt: str, max_new_tokens: int = 512) -> str:
    import torch

    model, tokenizer = _load_model()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a security-focused C/C++ code analyst. "
                "Always respond with valid JSON only — no markdown, no explanation outside the JSON."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    # Strip the prompt tokens from the output
    new_tokens = generated_ids[0][model_inputs.input_ids.shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
_DECISION_VALUES = {"likely_true", "likely_false", "uncertain"}
_DEFAULT_RECORD = {
    "llm_decision": "uncertain",
    "confidence": 0.5,
    "predicted_bug_type": None,
    "reasoning": None,
    "relevant_variables": [],
    "branch_conditions": [],
    "suspicious_locations": [],
}


def parse_response(raw: str, warning_id: str) -> Dict[str, Any]:
    """Extract JSON from model output; fall back gracefully on parse errors."""
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

    # Find outermost {...}
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        print(f"  WARNING [{warning_id}]: No JSON object found in model output.")
        return dict(_DEFAULT_RECORD)

    json_str = cleaned[start:end]
    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as exc:
        print(f"  WARNING [{warning_id}]: JSON parse error: {exc}")
        return dict(_DEFAULT_RECORD)

    # Validate / sanitise
    decision = parsed.get("llm_decision", "uncertain")
    if decision not in _DECISION_VALUES:
        decision = "uncertain"

    confidence = float(parsed.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return {
        "llm_decision": decision,
        "confidence": confidence,
        "predicted_bug_type": parsed.get("predicted_bug_type"),
        "reasoning": parsed.get("reasoning"),
        "relevant_variables": parsed.get("relevant_variables", []),
        "branch_conditions": parsed.get("branch_conditions", []),
        "suspicious_locations": parsed.get("suspicious_locations", []),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="LLM triage for static-analyzer warnings")
    parser.add_argument("--dataset", choices=["pilot", "juliet"], default="pilot")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_ANALYZER_OUTPUT,
        help="Path to clang_warnings.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_TRIAGE_OUTPUT,
        help="Path to write triaged_warnings.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N warnings (useful for testing)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Analyzer output not found: {args.input}")
        print("Run  python analyzer/run_clang_analyzer.py  first.")
        sys.exit(1)

    warnings: List[Dict[str, Any]] = json.loads(args.input.read_text())
    if args.limit:
        warnings = warnings[: args.limit]

    print(f"=== LLM Triage ({QWEN_MODEL_NAME}) ===")
    print(f"  Warnings to triage : {len(warnings)}")
    print(f"  Output             : {args.out}\n")

    template = load_prompt_template()
    results: List[Dict[str, Any]] = []

    for i, w in enumerate(warnings, 1):
        wid = w["warning_id"]
        print(f"  [{i}/{len(warnings)}] {wid}", end="  ", flush=True)
        t0 = time.perf_counter()

        prompt = build_prompt(w, template)
        raw = query_model(prompt)
        triage = parse_response(raw, wid)
        elapsed = time.perf_counter() - t0

        record = {
            "warning_id": wid,
            "llm_decision": triage["llm_decision"],
            "confidence": triage["confidence"],
            "predicted_bug_type": triage["predicted_bug_type"],
            "reasoning": triage["reasoning"],
            "relevant_variables": triage["relevant_variables"],
            "branch_conditions": triage["branch_conditions"],
            "suspicious_locations": triage["suspicious_locations"],
            "triage_time_s": round(elapsed, 3),
        }
        results.append(record)
        print(f"→ {triage['llm_decision']} ({triage['confidence']:.2f})  [{elapsed:.1f}s]")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2))

    counts = {v: sum(1 for r in results if r["llm_decision"] == v) for v in _DECISION_VALUES}
    print(f"\nResults: {counts}")
    print(f"Wrote {len(results)} triage records → {args.out}")


if __name__ == "__main__":
    main()

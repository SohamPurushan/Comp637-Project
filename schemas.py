"""
Pydantic/dataclass schemas for the pipeline data structures.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WarningRecord:
    """A warning emitted by Clang Static Analyzer."""

    warning_id: str
    file: str
    line: int
    column: int
    message: str
    checker: str
    category: str

    def model_dump(self) -> dict:
        return {
            "warning_id": self.warning_id,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "checker": self.checker,
            "category": self.category,
        }


@dataclass
class LLMTriageRecord:
    """Result of LLM triage on a static-analysis warning."""

    warning_id: str
    llm_decision: str  # "likely_true", "likely_false", "uncertain"
    confidence: float
    predicted_bug_type: Optional[str] = None
    reasoning: Optional[str] = None
    relevant_variables: List[str] = field(default_factory=list)
    branch_conditions: List[str] = field(default_factory=list)

    def model_dump(self) -> dict:
        return {
            "warning_id": self.warning_id,
            "llm_decision": self.llm_decision,
            "confidence": self.confidence,
            "predicted_bug_type": self.predicted_bug_type,
            "reasoning": self.reasoning,
            "relevant_variables": self.relevant_variables,
            "branch_conditions": self.branch_conditions,
        }


@dataclass
class SymExecTask:
    """A task to verify via symbolic execution."""

    warning_id: str
    target_file: str
    target_line: int
    expected_bug_type: str
    focus_variables: List[str] = field(default_factory=list)
    focus_conditions: List[str] = field(default_factory=list)


@dataclass
class SymExecResult:
    """Result of symbolic execution verification."""

    warning_id: str
    status: str  # "feasible", "infeasible", "timeout"
    details: str

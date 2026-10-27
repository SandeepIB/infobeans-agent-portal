from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    AUTO_FIXABLE = "AUTO_FIXABLE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    RECOMMENDATION_ONLY = "RECOMMENDATION_ONLY"

    # Backward compatibility aliases
    AUTO_FIX = "AUTO_FIXABLE"
    HUMAN_APPROVAL = "HUMAN_REVIEW_REQUIRED"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    # Backward compatibility alias
    CRITICAL = "HIGH"


class AgentStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    TIMEOUT = "TIMEOUT"


@dataclass
class Evidence:
    type: str = "slide_content"  # "slide_content" | "design_metadata" | "proposal_requirement"
    text: str = ""
    source_slide: int | None = None


@dataclass
class Expected:
    requirement_id: str | None = None
    text: str | None = None


@dataclass
class Finding:
    slide: int
    severity: Severity
    category: str
    title: str
    description: str
    recommendation: str
    confidence: float = 0.8
    action_type: ActionType = ActionType.RECOMMENDATION_ONLY
    id: str | None = None
    rule_id: str | None = None
    prompt_version_id: int | None = None
    evidence: str | Evidence | None = None
    expected: Expected | None = None

    @property
    def evidence_text(self) -> str:
        if isinstance(self.evidence, Evidence):
            return self.evidence.text
        return str(self.evidence or "")


@dataclass
class AgentContract:
    agent_id: str
    status: AgentStatus | str   # Standard enum or string
    score: int                  # 0–100
    findings: list[Finding] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.85    # Agent assessment confidence (0.00 - 1.00)
    metadata: dict[str, Any] = field(default_factory=dict)


class ReviewAgent(ABC):
    agent_id: str

    @abstractmethod
    def run(self, context: dict) -> AgentContract:
        """Run the agent. Always returns AgentContract — never raises."""

    def _failed(self, reason: str) -> AgentContract:
        return AgentContract(
            agent_id=self.agent_id,
            status=AgentStatus.FAILED,
            score=0,
            summary=f"Agent failed: {reason}",
            confidence=0.0,
        )


# Agent Contract — Development Guide

## Purpose

Every agent returns the Standard Agent Contract. This document covers how to implement it correctly.
For the canonical schema, see: [../architecture/04-agent-contract.md](../architecture/04-agent-contract.md)

## Rules

1. Every agent — rule-based or LLM-based — returns the standard contract. No exceptions.
2. No free text exits an agent boundary.
3. If the LLM would return prose, wrap it in a structured-output schema and validate before returning.
4. If validation fails after retries, return `status: failed` — do not return partial data.

## Python Implementation Pattern

### Agent Base Class (`agents/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class ActionType(str, Enum):
    AUTO_FIX = "AUTO_FIX"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    RECOMMENDATION_ONLY = "RECOMMENDATION_ONLY"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class Finding:
    slide: int
    severity: Severity
    category: str
    title: str
    description: str
    recommendation: str
    confidence: float
    action_type: ActionType
    rule_id: str | None
    prompt_version_id: int | None

@dataclass
class AgentContract:
    agent_id: str
    status: str  # "completed" | "failed" | "skipped"
    score: int   # 0–100
    findings: list[Finding]
    summary: str

class ReviewAgent(ABC):
    @abstractmethod
    def run(self, context: dict) -> AgentContract:
        """Run the agent and return the standard contract."""
```

### LLM Agent Pattern

```python
class ContentAgent(ReviewAgent):
    def run(self, context: dict) -> AgentContract:
        prompt_version = self.prompt_service.get_active(self.agent_id, context["review_profile"])
        rendered = self.prompt_service.render(prompt_version, self._build_variables(context))

        response = self.llm_provider.complete(
            system=rendered.system_role,
            user=rendered.user_message,
            schema=rendered.output_schema,   # enforce structured output
        )

        # validate and build contract — never pass raw response downstream
        return self._parse_response(response, prompt_version.id)
```

### Rule Agent Pattern

```python
class BrandingAgent(ReviewAgent):
    def run(self, context: dict) -> AgentContract:
        rules = self.rule_service.get_active("branding")
        findings = []
        for rule in rules:
            result = rule.check(context["design_metadata"])
            if result.violation:
                findings.append(Finding(
                    slide=result.slide,
                    severity=rule.severity,
                    action_type=ActionType.AUTO_FIX if rule.auto_fixable else ActionType.HUMAN_APPROVAL,
                    confidence=1.0,      # rule-based: always 1.0
                    rule_id=rule.rule_id,
                    prompt_version_id=None,
                    ...
                ))
        return AgentContract(agent_id=self.agent_id, status="completed", ...)
```

## Failure Handling

```python
# On exception: return failed contract, do not propagate
try:
    result = self._run_internal(context)
except Exception as e:
    logger.error(f"Agent {self.agent_id} failed: {e}")
    return AgentContract(
        agent_id=self.agent_id,
        status="failed",
        score=0,
        findings=[],
        summary=f"Agent failed: {str(e)}"
    )
```

## Related Documents

- See: [../architecture/04-agent-contract.md](../architecture/04-agent-contract.md) for canonical schema
- See: [../prompts/prompt-lifecycle.md](../prompts/prompt-lifecycle.md) for PromptService
- See: [../rules/rule-library.md](../rules/rule-library.md) for RuleService
- See: [../development/testing.md](../development/testing.md) for MockProvider testing

# Score Governance — NOW

## Purpose

Define how agent scores are aggregated into the review score, and how critical findings override
numeric readiness gates.

## Agent Score Weights

```yaml
score_weights:
  template:         0.10
  branding:         0.10
  security:         0.15
  accessibility:    0.08
  content:          0.15
  story:            0.10
  customer_focus:   0.12
  proposal_context: 0.15   # only when enabled
  cio_lens:         0.05
  # critic does not contribute to score (it reconciles; it does not evaluate independently)
```

Weights are configurable per Review Profile. They do not live in code.

## Category Weights Within Each Agent

Each agent can return findings across multiple categories. Category weights are declared in the
agent's configuration (not in agent code).

## Severity Weighting

Findings deduct points from an agent's raw score based on severity:

| Severity | Score deduction |
|---------|-----------------|
| LOW | 2 |
| MEDIUM | 5 |
| HIGH | 15 |
| CRITICAL | 40 |

Minimum agent score: 0 (cannot go negative).

## Readiness Thresholds

```yaml
readiness_thresholds:
  READY:   score >= 85 AND no CRITICAL findings AND no unresolved HUMAN_APPROVAL findings
  REVIEW:  score >= 65 AND no CRITICAL findings
  BLOCKED: score < 65 OR any CRITICAL finding OR unresolved HUMAN_APPROVAL findings > configured_limit
```

## Critical Finding Override

**A high numeric score does NOT override a critical finding.**

```
Aggregated score: 94
Critical finding: 1 (security vulnerability found)

Final status: BLOCKED (score is irrelevant)
```

This rule is non-negotiable. The orchestrator enforces it — not the LLM.

## Score Explainability

The review result must include:
- Final readiness status
- Overall score
- Per-agent score
- Per-finding score contribution
- Reason for BLOCKED status if applicable

Example:
```json
{
  "score": 94,
  "readiness": "BLOCKED",
  "blocked_reason": "1 CRITICAL finding: Security Agent found undisclosed financial data",
  "agent_scores": {
    "template": 98,
    "branding": 95,
    "security": 0,
    "content": 91
  }
}
```

## Related Documents

- See: [finding-management.md](finding-management.md) for finding deduplication
- See: [confidence.md](confidence.md) for confidence and severity interaction
- See: [04-agent-contract.md](04-agent-contract.md) for severity field definitions

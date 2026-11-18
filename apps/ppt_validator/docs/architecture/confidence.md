# Confidence Calibration — NOW

## Purpose

Define what confidence means, how it is used, and how low-confidence critical findings are handled.

## Confidence Definition

Confidence is the agent's (or LLM's) estimated probability that the finding is correct.

| Range | Label | Meaning |
|-------|-------|---------|
| 0.90–1.00 | High | Finding is almost certainly correct |
| 0.70–0.89 | Medium | Finding is likely correct; some uncertainty |
| 0.50–0.69 | Low | Finding may be correct; significant uncertainty |
| < 0.50 | Very Low | Finding should not be surfaced to user |

## Rules

- Findings with `confidence < 0.50` are filtered out before the Critic stage.
- Findings with `confidence < 0.70` and `severity = CRITICAL` receive special handling (see below).
- Confidence is set by the agent; it is not post-processed or adjusted by the orchestrator.
- Rule-based agents always return `confidence = 1.0` (deterministic findings have no uncertainty).

## Low-Confidence Critical Finding Handling

A `severity = CRITICAL` finding with `confidence < 0.70` is escalated to human review:

```
Critical finding, confidence 0.65
     │
     ▼
action_type forced to HUMAN_APPROVAL
     │
Finding note: "Confidence below threshold — requires human verification before action"
     │
Reviewer must confirm or dismiss
```

## Confidence in the UI

- Show confidence as a percentage or label (High/Medium/Low) per finding.
- Allow users to filter findings by confidence level.
- On human feedback (accept/reject), record whether the finding confidence was appropriate.

## Calibration Over Time

Accepted findings with low confidence → model may be under-confident.
Rejected findings with high confidence → model may be over-confident.

Human feedback dataset tracks this. Use it for prompt improvement.
See: [../evaluation/human-feedback.md](../evaluation/human-feedback.md)

## Related Documents

- See: [finding-management.md](finding-management.md) for deduplication
- See: [scoring.md](scoring.md) for how confidence affects scoring
- See: [04-agent-contract.md](04-agent-contract.md) for confidence field definition

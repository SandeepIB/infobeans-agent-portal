# Finding Deduplication and Management — NOW

## Purpose

Multiple agents may detect the same issue. Deduplicate deterministically while preserving provenance.
Never lose which agents detected a finding.

## Problem

Content Agent, CIO Lens, and Customer Agent may all flag "slide 8 is too technical for the audience."
The user should see one canonical finding, not three duplicates.

## Finding Correlation Service

```python
class FindingCorrelationService:
    def deduplicate(self, findings: list[Finding]) -> list[CanonicalFinding]:
        """
        Groups findings by (slide, category, description_similarity).
        For each group, produces one canonical finding with:
            - Highest severity from the group
            - Most specific recommendation
            - All source agent_ids recorded
            - Highest confidence from the group
            - Strictest action_type (HUMAN_APPROVAL > RECOMMENDATION_ONLY > AUTO_FIX)
        """
```

## Deduplication Rules

1. Same slide + same category + description similarity > threshold → same issue
2. Canonical finding uses the most severe severity from the group
3. Canonical finding uses the strictest action_type from the group
4. All source `agent_id`s are recorded in `source_agents` list
5. Provenance is never lost — the UI can show "detected by: Content Agent, CIO Lens"

## Canonical Finding Schema

```json
{
  "finding_id": "fnd_abc123",
  "slide": 8,
  "severity": "HIGH",
  "category": "customer_relevance",
  "title": "Too technical for executive audience",
  "description": "...",
  "recommendation": "...",
  "confidence": 0.91,
  "action_type": "RECOMMENDATION_ONLY",
  "source_agents": ["content", "cio_lens", "customer_focus"],
  "prompt_version_ids": { "content": 5, "cio_lens": 2, "customer_focus": 3 },
  "rule_id": null
}
```

## Finding Severity

Severity escalates — never de-escalates — during deduplication:

```
Agent A: MEDIUM
Agent B: HIGH
Agent C: MEDIUM
→ Canonical: HIGH
```

## Finding Action Type

Action type uses the strictest value during deduplication:

```
Agent A: RECOMMENDATION_ONLY
Agent B: HUMAN_APPROVAL
→ Canonical: HUMAN_APPROVAL
```

## UI Display

- Show canonical finding with "detected by N agents" indicator
- Allow user to expand to see each agent's original finding
- Show confidence range across source agents

## Related Documents

- See: [04-agent-contract.md](04-agent-contract.md) for finding schema
- See: [scoring.md](scoring.md) for how findings affect score
- See: [confidence.md](confidence.md) for confidence handling

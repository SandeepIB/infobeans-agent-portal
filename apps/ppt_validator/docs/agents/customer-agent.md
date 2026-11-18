# Customer Focus Agent

## Purpose

Evaluate whether the deck is appropriately framed for the specified customer and audience.
Identifies technical jargon inappropriate for the audience, missing customer outcomes,
and messaging that does not connect to the customer's stated concerns.

## Inputs

- `normalized_slides` — slide content
- `review_profile` — customer name, audience, industry, objective

## Context Scope

```yaml
context_scope:
  slides: all
  content: full
  design: none
  findings: none
```

## Categories

| Category | Description |
|----------|-------------|
| `customer_relevance` | Is content relevant to this specific customer? |
| `audience_framing` | Is framing appropriate for the audience level? |
| `outcome_focus` | Are customer outcomes emphasised over internal capabilities? |
| `tone` | Is tone appropriate for the audience? |

## DAG Position

Parallel with Content, Story, Proposal agents after content extraction.

## Registry Entry

```yaml
agent_id: customer_focus
type: llm
version: 1
execution_mode: parallel
dependency_stage: content_extraction
requires: [ppt_content]
severity_default: MEDIUM
enabled_by_default: true
cacheability: full
```

## Testing

- Test: executive-framed content for CTO audience → high score
- Test: implementation-heavy slide for CEO → HIGH finding
- Test: no customer name context in profile → agent runs with generic audience guidance

## Related Documents

- See: [cio-lens.md](cio-lens.md) for executive-level evaluation
- See: [proposal-agent.md](proposal-agent.md) for proposal-specific customer framing

# Content Agent

## Purpose

Evaluate slide content quality: clarity, relevance, depth, structure, and alignment with the
stated audience and objective.

## Inputs

- `normalized_slides` — slide text, titles, bullets per slide
- `review_profile` — audience, objective, industry

## Outputs

- Standard Agent Contract with per-slide content findings
- `deck_summary` — one-sentence summary per slide (used by CIO Lens)

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
| `content_clarity` | Is the slide message clear? |
| `content_depth` | Appropriate depth for audience? |
| `content_relevance` | Relevant to objective? |
| `content_structure` | Well-structured bullets/flow? |

## DAG Position

Runs in parallel with Story, Customer, Proposal agents after content extraction.

## Prompt

Location: `prompts/content_agent/v1.yaml`

## Registry Entry

```yaml
agent_id: content
type: llm
version: 1
execution_mode: parallel
dependency_stage: content_extraction
requires: [ppt_content]
severity_default: MEDIUM
enabled_by_default: true
cacheability: slide_level
```

## Testing

- Test: clear, concise slide → no finding or LOW finding
- Test: jargon-heavy slide for executive audience → HIGH finding
- Test: empty slide → MEDIUM finding

## Related Documents

- See: [../architecture/07-context-flow.md](../architecture/07-context-flow.md) for context scope
- See: [agent-contract.md](agent-contract.md) for output format

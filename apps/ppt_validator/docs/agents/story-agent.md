# Story Agent

## Purpose

Evaluate the deck's narrative arc: logical flow, transitions, opening hook, closing call-to-action,
and whether the story builds toward the stated objective.

## Inputs

- `slide_sequence` — slide titles + one-sentence summaries in order (not full content)
- `review_profile` — objective, audience

## Context Scope

Story Agent receives titles and summaries — not full slide content. This keeps context small.

```yaml
context_scope:
  slides: all
  content: title_only     # plus one-sentence summary
  design: none
  findings: none
```

## Categories

| Category | Description |
|----------|-------------|
| `narrative_flow` | Does the story flow logically? |
| `opening_hook` | Does the opening engage the audience? |
| `closing_cta` | Is there a clear call-to-action? |
| `transitions` | Are slide transitions logical? |

## DAG Position

Parallel with Content, Customer, Proposal agents after content extraction.

## Registry Entry

```yaml
agent_id: story
type: llm
version: 1
execution_mode: parallel
dependency_stage: content_extraction
requires: [slide_sequence]
severity_default: MEDIUM
enabled_by_default: true
cacheability: full
```

## Testing

- Test: logical narrative arc → high score
- Test: no clear closing → MEDIUM finding
- Test: slides in illogical order → HIGH finding

## Related Documents

- See: [agent-contract.md](agent-contract.md) for output format
- See: [cio-lens.md](cio-lens.md) for executive narrative evaluation

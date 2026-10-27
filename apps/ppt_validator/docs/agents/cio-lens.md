# CIO Lens Agent

## Purpose

Evaluates the deck from an executive (CIO/CTO/CEO) perspective. Operates on the full deck summary,
not individual slides. Identifies executive-level narrative gaps, missing strategic messaging, and
presentation-level quality issues.

## Inputs

- `deck_summary` — compressed summary of all slides (from Content Agent output, not raw content)
- `key_findings` — deduplicated findings from Content, Story, Customer, and Proposal agents
- `review_profile` — audience, industry, objective

## Outputs

Standard Agent Contract. Score reflects executive-level readiness.

## What It Evaluates

- Is the opening compelling for an executive audience?
- Is the strategic narrative clear and coherent?
- Is the value proposition stated with evidence?
- Are the key risks acknowledged and addressed?
- Does the deck feel complete for the stated objective?
- Are there slide-level issues that undermine executive confidence?

## Context Scope

CIO Lens receives summaries, not raw slide content. This is intentional — it evaluates the
executive experience, not slide-by-slide detail.

```yaml
context_scope:
  slides: none              # receives deck summary, not raw slides
  content: summary          # compressed deck summary from Content Agent
  design: none
  findings: filtered        # high-severity findings from other agents
  proposal_context: full    # when available
```

## DAG Position

Runs after Content, Story, Customer, and Proposal agents. Before Critic.
Receives their output as summarized context.

## Prompt

Location: `prompts/cio_lens/v1.yaml`

Strong model recommended (see [../architecture/model-routing.md](../architecture/model-routing.md)).

## Registry Entry

```yaml
agent_id: cio_lens
type: llm
version: 1
execution_mode: sequential
dependency_stage: cross_slide
requires: [deck_summary, key_findings]
severity_default: MEDIUM
enabled_by_default: true
cacheability: full
```

## Testing

- Test: strong deck → high score, few findings
- Test: weak executive narrative → MEDIUM findings
- Test: missing value proposition → HIGH finding

## Related Documents

- See: [../architecture/07-context-flow.md](../architecture/07-context-flow.md) for context scope
- See: [../architecture/02-agent-dag.md](../architecture/02-agent-dag.md) for DAG position

# Agent Registry

## Purpose

The Agent Registry is the single source of truth for what agents exist, their type, and their DAG
position. The orchestrator reads the registry — it never hard-codes agent lists.

## Registry Entry Schema

```yaml
agent_id: <string>              # unique identifier, snake_case
name: <string>                  # human-readable name
type: rule | llm | hybrid       # execution type
version: <integer>              # registry entry version
execution_mode: parallel | sequential
dependency_stage: extraction | content_extraction | aggregation | cross_slide
requires:                       # inputs this agent needs
  - ppt_content
  - proposal_context            # optional inputs listed here
severity_default: LOW | MEDIUM | HIGH | CRITICAL
enabled_by_default: true | false
context_scope: <string>         # what slice of PPT context this agent needs
cacheability: full | slide_level | none
```

## Current Agent Registry

| agent_id | type | dependency_stage | execution_mode | enabled_by_default |
|----------|------|-----------------|----------------|-------------------|
| `template` | rule | extraction | parallel | true |
| `branding` | rule | extraction | parallel | true |
| `security` | rule | extraction | parallel | true |
| `accessibility` | hybrid | extraction | parallel | true |
| `slide_design_match` | rule | extraction | sequential | false |
| `content` | llm | content_extraction | parallel | true |
| `story` | llm | content_extraction | parallel | true |
| `customer_focus` | llm | content_extraction | parallel | true |
| `proposal_context` | llm | content_extraction | parallel | false |
| `cio_lens` | llm | cross_slide | sequential | true |
| `critic` | llm | cross_slide | sequential | true |
| `fix` | hybrid | aggregation | sequential | true |

## Rules

- Every agent must have a registry entry before it runs.
- `enabled_by_default: false` means the agent only runs when a Review Profile explicitly enables it.
- The orchestrator resolves the execution plan from the registry + Review Profile at request time.
- Do not add agent-specific conditional logic in `ReviewService`.

## Adding an Agent

See: [../development/adding-agent.md](../development/adding-agent.md)

## Related Documents

- See: [02-agent-dag.md](02-agent-dag.md) for DAG structure
- See: [04-agent-contract.md](04-agent-contract.md) for output contract
- See: [05-review-profiles.md](05-review-profiles.md) for enabling agents per profile

# Agent Registry — Development Guide

## Purpose

The Agent Registry is the single source of truth for all agents. The orchestrator reads it at runtime.
Do not add agent-specific logic to `ReviewService`.

## Registry Location

DB table `agent_registry`. Seed entries from `agents/registry.yaml` on first startup.

## Registry Entry Schema

See: [../architecture/03-agent-registry.md](../architecture/03-agent-registry.md)

## How to Register a New Agent

1. Add entry to `agents/registry.yaml` (seed file).
2. Run `python db/migrate.py` (idempotent — will insert if not present).
3. Add agent to relevant Review Profiles.

## How the Orchestrator Uses the Registry

```python
class ReviewService:
    def build_execution_plan(self, review_profile: ReviewProfile) -> ExecutionPlan:
        agents = registry.get_enabled(review_profile)
        plan = DAGBuilder.build(agents)  # resolves dependency_stage ordering
        return plan
```

The orchestrator reads the registry. It never hard-codes agent names or execution order.

## Agent Context Scope Declaration

```yaml
agent_id: content
context_scope:
  slides: all
  content: full
  design: none
  findings: none
  proposal_context: none
```

`ContextBuilder` uses `context_scope` to slice the review context for each agent call.

## Related Documents

- See: [../architecture/03-agent-registry.md](../architecture/03-agent-registry.md) for full schema
- See: [../development/adding-agent.md](../development/adding-agent.md) for step-by-step guide
- See: [../architecture/05-review-profiles.md](../architecture/05-review-profiles.md) for profiles

# Incremental Re-review — NOW

## Purpose

After a fix, re-review only the agents affected by the change.
Never rerun the full pipeline when only a subset of agents is invalidated.

## Problem

A full re-review after fixing a font size wastes tokens and time running Content, Story, Proposal,
and CIO Lens agents on content that did not change.

## Change Detection

`ChangeDetectorService` compares old PPT vs. new PPT:

```python
class ChangeDetectorService:
    def detect(self, old_ppt_version_id: str, new_ppt_version_id: str) -> ChangeSet:
        """
        Returns:
            changed_slides: list of slide numbers that changed
            change_types: set of change domains (design | content | structure)
        """
```

## Agent Dependency Declarations

Each agent declares in the registry what changes invalidate its results:

```yaml
agent_id: branding
affected_by:
  - design
  - slide_indices: all    # any slide change invalidates branding

agent_id: content
affected_by:
  - content               # only content changes invalidate this agent

agent_id: story
affected_by:
  - content
  - structure             # slide additions/deletions invalidate story

agent_id: template
affected_by:
  - design

agent_id: cio_lens
affected_by:
  - content
  - structure             # CIO lens needs to see the full picture if anything content changes
```

## Invalidation Rules

```
ChangeSet (slide 8: design changed)
     │
For each agent in review:
  Check agent.affected_by against ChangeSet.change_types
  If match → agent is INVALIDATED → must rerun
  If no match → agent result is REUSED (from cache / prior run)
```

## Re-review Plan

```
Fix applied to slide 8 (font size)
Change type: design

Invalidated agents: template, branding, accessibility (partial)
Reused agents:      content, story, customer, proposal_context, cio_lens, critic

Re-review runs only: template, branding, accessibility
Final result: merged (new results for design agents + reused results for content agents)
```

## Cacheability

Each agent declares its cacheability:

```yaml
cacheability: full        # result is fully cacheable if inputs unchanged
cacheability: slide_level # result is cacheable per slide independently
cacheability: none        # always rerun (e.g., Critic which depends on all other findings)
```

## Rules

- The orchestrator determines what must rerun — not an LLM.
- Never automatically rerun everything. Always use `ChangeDetectorService`.
- Reused results from the prior run must be explicitly marked as reused in the new audit trail.
- The Critic always reruns if any agent reran (findings may have changed).

## Related Documents

- See: [09-fix-rereview.md](09-fix-rereview.md) for fix loop
- See: [../operations/caching.md](../operations/caching.md) for LLM response cache
- See: [03-agent-registry.md](03-agent-registry.md) for agent declarations

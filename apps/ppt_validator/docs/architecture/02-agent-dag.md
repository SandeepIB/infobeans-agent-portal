# Agent DAG — Execution Model

## Purpose

The orchestrator builds an execution plan from the Agent Registry and Review Profile, then runs it
as a DAG. No LLM decides execution order. The orchestrator is deterministic.

## DAG

```
Review Request
│
├── PPTX (required)
├── Review Profile (required)
├── Reference Template PPT (optional) ← Slide Design Match
└── Proposal Context (optional)        ← Proposal Agent

                Extraction (always first)
                       │
         ┌─────────────┼──────────────┐
         │             │              │
    Template       Branding       Security
    Accessibility
         │
         ▼
    [Slide Design Match Filter]  ← if reference PPT provided,
         │                          matched slides excluded from downstream design agents
         ▼
    Content Extraction
         │
    ┌────┼──────────────┬────────────────┐
    │    │              │                │
 Content Story      Customer        Proposal
 Agent  Agent        Agent           Context
                          │               │
                          └──────┬────────┘
                                 ▼
                      Cross-Slide / CIO Lens
                                 │
                                 ▼
                             Critic
                                 │
                                 ▼
                  Aggregator → score + findings + severity
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
           Human Review                    Fix Agent
        (HUMAN_APPROVAL /               (AUTO_FIX only)
         RECOMMENDATION_ONLY)                  │
                                               ▼
                                     New PPT → Re-review
                                         (incremental)
                                 │
                                 ▼
          Customer Quality Gate: 🟢 READY / 🟡 REVIEW / 🔴 BLOCKED
```

## Rules for Adding a New Agent

1. Register in Agent Registry (`agent_id`, `type`, `execution_mode`, `dependency_stage`).
2. Give it a Review Profile toggle — enable/disable per profile without code changes.
3. Do NOT add `if agent_name == "..."` branching in `ReviewService`. The orchestrator reads the registry.
4. Define which extraction stage it depends on.
5. Declare its context scope (only what it needs).
6. Write a `MockProvider`-backed unit test.

See: [../development/adding-agent.md](../development/adding-agent.md)

## Parallel vs Sequential

- Agents at the same DAG level run in parallel by default.
- Sequential execution only where one agent depends on another's output.
- The orchestrator resolves dependency ordering from the registry — not from code branching.

## Re-review After Fix

After a fix, only agents invalidated by the fix rerun.
See: [incremental-review.md](incremental-review.md)

## Related Documents

- See: [03-agent-registry.md](03-agent-registry.md) for registry schema
- See: [04-agent-contract.md](04-agent-contract.md) for agent output contract
- See: [05-review-profiles.md](05-review-profiles.md) for profile configuration
- See: [09-fix-rereview.md](09-fix-rereview.md) for fix loop
- See: [execution-controls.md](execution-controls.md) for concurrency limits

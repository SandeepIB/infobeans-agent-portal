# Fix Agent and Re-review Loop

## Purpose

After review, the Fix Agent applies mechanical corrections. A re-review runs on the fixed PPT.
Re-review is incremental — only agents affected by the fix rerun.

## Fix Agent Rules

- Only touches findings marked `action_type: AUTO_FIX`.
- Never applies `HUMAN_APPROVAL` or `RECOMMENDATION_ONLY` findings, even if prompted to.
- Every fix is logged in `fix_operations` (what changed, which finding, before/after state).
- After fixing, always triggers re-review — never re-scores by assumption.

## Fix Loop

```
Review Result
     │
AUTO_FIX findings
     │
User approves fix run
     │
FixService
├── Read each AUTO_FIX finding
├── Apply mechanical correction to PPT
├── Log fix_operations row
└── Produce new PPT version

New PPT version
     │
Incremental Re-review (not full re-review)
     │
Change detector identifies affected agents
     │
Re-run only affected agents
     │
New Review Result
```

## What Can Be AUTO_FIX

| Finding | Reason |
|---------|--------|
| Body font below minimum size | Mechanical: resize to minimum |
| Brand color code incorrect | Mechanical: replace color value |
| Missing slide number | Mechanical: insert |
| Logo position off-template | Mechanical: reposition if template anchor is unambiguous |

## What Must Never Be AUTO_FIX

| Finding | Reason |
|---------|--------|
| Missing requirement coverage | Business decision |
| Incorrect client claim | Legal/reputational risk |
| Scope contradiction | Contractual |
| Win theme not evidenced | Content quality judgment |
| Any pricing-related | Financial commitment |

## Incremental Re-review

After fix, use `ChangeDetectorService` to identify:
1. Which slides changed (by diff)
2. Which agents are sensitive to those changes
3. Rerun only those agents

See: [incremental-review.md](incremental-review.md) for full dependency invalidation rules.

## Related Documents

- See: [../agents/fix-agent.md](../agents/fix-agent.md) for Fix Agent specification
- See: [incremental-review.md](incremental-review.md) for incremental re-review
- See: [04-agent-contract.md](04-agent-contract.md) for action_type definitions

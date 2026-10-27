# Fix Agent

## Purpose

Apply mechanical corrections to the PPT for findings marked `action_type: AUTO_FIX`.
Never apply `HUMAN_APPROVAL` or `RECOMMENDATION_ONLY` findings.

## Inputs

- `pptx_version_id` — the PPT to fix
- `findings` — list of `AUTO_FIX` findings to apply

## Outputs

- `fixed_pptx_version_id` — new PPT artifact
- `fix_operations` — log of what was changed

## Rules

1. Only `AUTO_FIX` findings. If a finding is not `AUTO_FIX`, skip it and log the skip.
2. Every fix is logged in `fix_operations` (before/after, which finding, which slide).
3. After fixing, always trigger incremental re-review — never re-score by assumption.
4. If a fix cannot be applied mechanically (ambiguous position, unsupported format), skip with WARNING.

## What Can Be Fixed

| Finding | Fix action |
|---------|-----------|
| Body font below minimum size | Resize font to minimum configured value |
| Brand color code incorrect | Replace hex color value |
| Missing slide number | Insert slide number at configured position |
| Logo position off-template | Reposition to template anchor (if unambiguous) |

## What Must Never Be Fixed by the Fix Agent

| Finding | Reason |
|---------|--------|
| Missing requirement coverage | Business decision |
| Incorrect client claim | Legal/reputational |
| Scope contradiction | Contractual |
| Any content quality issue | Subjective |
| Any `HUMAN_APPROVAL` finding | Never auto-applied |

## Prompt

Location: `prompts/fix_agent/v1.yaml`

Used for determining the exact fix action when the correction is not purely mechanical.
Rule-based fixes (font size, color code) do not use the LLM.

## Registry Entry

```yaml
agent_id: fix
type: hybrid
version: 1
execution_mode: sequential
dependency_stage: aggregation
requires: [pptx, auto_fix_findings]
enabled_by_default: true
```

## Testing

- Test: font size finding → font resized correctly
- Test: `HUMAN_APPROVAL` finding in input → skipped; not applied
- Test: fix fails → logged as skipped; pipeline continues

## Related Documents

- See: [../architecture/09-fix-rereview.md](../architecture/09-fix-rereview.md) for fix loop
- See: [../architecture/incremental-review.md](../architecture/incremental-review.md) for re-review
- See: [../architecture/04-agent-contract.md](../architecture/04-agent-contract.md) for action_type

# Human Feedback Loop — NEXT

## Purpose

Capture structured human feedback on findings to improve prompt quality over time.
Do not automatically modify prompts from a single feedback event.

## Feedback Flow

```
Finding displayed to reviewer
         │
Reviewer action:
  ├── Accept  → finding is correct
  ├── Reject  → finding is wrong; reason required
  └── Modify  → finding is partially correct; reviewer provides correction
         │
         ▼
Feedback stored in feedback_dataset
         │
         ▼
Batch analysis (periodic, not automatic)
         │
         ▼
Identifies prompt improvement opportunities
         │
         ▼
Engineer creates new prompt version (draft)
         │
         ▼
Evaluation gates (see evaluation-gates.md)
         │
         ▼
Activation (if gates pass)
```

## Feedback Schema

```json
{
  "feedback_id": "fb_abc123",
  "finding_id": "fnd_xyz",
  "review_run_id": "rrn_...",
  "agent_id": "content",
  "prompt_version_id": 5,
  "action": "reject",
  "reason": "The slide actually targets a developer audience, not an executive",
  "corrected_severity": null,
  "corrected_action_type": null,
  "corrected_recommendation": null,
  "reviewer_id": "user_123",
  "reviewed_at": "2025-01-15T10:30:00Z"
}
```

## DB Table

```sql
CREATE TABLE IF NOT EXISTS human_feedback (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id             TEXT NOT NULL,
    review_run_id          TEXT NOT NULL,
    agent_id               TEXT NOT NULL,
    prompt_version_id      INTEGER,
    action                 TEXT NOT NULL,   -- accept | reject | modify
    reason                 TEXT,
    corrected_severity     TEXT,
    corrected_action_type  TEXT,
    corrected_recommendation TEXT,
    reviewer_id            TEXT NOT NULL,
    reviewed_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Rules

- Do not automatically train or modify prompts from a single feedback event.
- Batch analysis is a periodic manual process, not an automatic pipeline.
- Feedback must be versioned: `prompt_version_id` recorded with each feedback item.
- Feedback from different prompt versions must not be mixed in the same analysis.
- Human feedback data is retained indefinitely — never deleted.

## Calibration Signal

Feedback events over time identify:
- Agents with consistently high reject rates → prompt needs improvement
- Finding categories with high reject rates → category prompt needs refinement
- Confidence miscalibration (high-confidence rejections = over-confident)

## Phase 1 Simplification

In Phase 1, feedback is collected and stored. Batch analysis is manual.
The automated analysis pipeline is NEXT.

## Related Documents

- See: [evaluation.md](evaluation.md) for TruLens evaluation framework
- See: [../architecture/confidence.md](../architecture/confidence.md) for confidence calibration
- See: [../prompts/prompt-lifecycle.md](../prompts/prompt-lifecycle.md) for prompt improvement process

# Excluded Slides — NOW

## Purpose

Support excluding specific slides from specific agents, with a full audit trail.
Never silently exclude content — every exclusion is logged and visible.

## Exclusion Sources

| Source | Mechanism | Default Reference |
|--------|-----------|-------------------|
| Slide Design Match | Matched slides excluded from design agents (Template, Branding) | `/var/www/html/Ib-ppt-validator/slide_templates/Exclude Slides.pptx` |
| User-defined exclusion | User explicitly excludes a slide via API/UI | N/A |
| Agent-level scope | Slide type (e.g., divider slide) excluded from content agents | N/A |

## Exclusion Schema

```json
{
  "exclusion_id": "exc_abc123",
  "slide_number": 3,
  "excluded_agents": ["template", "branding"],
  "reason": "slide_design_match",
  "detail": "Matches Exclude Slides.pptx slide 1 with score 0.95",
  "scope": "design_agents",
  "excluded_by": "system",
  "timestamp": "2025-01-15T10:30:00Z",
  "reference_template_id": "Exclude Slides.pptx",
  "reference_template_version": 1
}
```

## Exclusion Reason Codes

| reason | Description |
|--------|-------------|
| `slide_design_match` | Slide matches reference template |
| `user_requested` | User explicitly excluded |
| `slide_type` | Slide type (e.g., blank, divider) excluded by profile config |

## Scope Values

| scope | Excluded agents |
|-------|----------------|
| `design_agents` | template, branding (not content, story, customer, security) |
| `content_agents` | content, story, customer (not design agents) |
| `all_agents` | All agents (slide completely excluded) |
| Custom | Per `excluded_agents` list |

## Audit Trail

Every exclusion is recorded in `slide_exclusions` table:

```sql
CREATE TABLE IF NOT EXISTS slide_exclusions (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id          TEXT NOT NULL,
    slide_number           INTEGER NOT NULL,
    excluded_agents        TEXT NOT NULL,  -- JSON array
    reason                 TEXT NOT NULL,
    detail                 TEXT,
    excluded_by            TEXT NOT NULL,
    reference_template_id  TEXT,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## UI Display

- "Design Matched" badge on slides excluded by Slide Design Match.
- Tooltip: "This slide matches the approved reference template. Design agents were not applied."
- Excluded slides still appear in content findings if content agents ran.
- Review result summary shows excluded slide count with reason breakdown.

## Rules

- Never silently exclude slides. Every exclusion is recorded.
- Content exclusions require explicit user action (never automatic).
- Design exclusions from Slide Design Match are automatic but logged.
- Exclusion audit trail is included in reproducibility record.

## Related Documents

- See: [../agents/slide-design-match.md](../agents/slide-design-match.md) for design match exclusion
- See: [reproducibility.md](reproducibility.md) for exclusion in audit trail
- See: [05-review-profiles.md](05-review-profiles.md) for profile-level exclusion config

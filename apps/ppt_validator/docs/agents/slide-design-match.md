# Slide Design Match

## Purpose

When a Reference Template PPT is provided, match slides in the review deck against it.
Slides that match are excluded from design-layer review agents (Template, Branding).
Content, Story, Proposal, and Security agents still run on all slides.

## Inputs

- `pptx` — the deck under review
- `reference_template_ppt` — optional; defaults to `/var/www/html/Ib-ppt-validator/slide_templates/Exclude Slides.pptx`

## Outputs

- `matched_slide_indices` — list of slide numbers that matched the reference template
- `match_filter_status` — `active | unavailable | skipped`

## Matching Algorithm

Structural and visual — not pixel-perfect:

| Signal | Weight |
|--------|--------|
| Slide layout name | High (0.25) |
| Text & title similarity / Content hash | High (0.35) |
| Placeholder count + types | Medium (0.15) |
| Image presence & count | Medium (0.15) |
| Background color & fonts | Low (0.10) |

A slide is **matched** when weighted similarity score ≥ configured threshold (default `0.80`).

## Agents & Checks That Honour Exclusion

| Check / Agent | Respects match exclusion? | Notes |
|---------------|--------------------------|-------|
| Template Layout Agent | **Yes — excluded** | Slide layout structure & slide count rules skipped |
| Branding (Logo & Background Color) | **Yes — excluded** | Logo presence/position/size and slide background colors skipped |
| Branding (Font Guidelines) | **No — STILL CHECKED** | Font mismatches (non-brand fonts) are always reported |
| Branding (Pagination Guidelines) | **No — STILL CHECKED** | Pagination presence/position/font/size/color are always reported |
| Content Agent | **No** | Full content review runs |
| Story Agent | **No** | Full narrative flow review runs |
| Security Agent | **No** | Full security review runs |

## Review Profile Configuration

```json
{
  "slide_design_match": {
    "enabled": true,
    "exclude_template_path": "/var/www/html/Ib-ppt-validator/slide_templates/Exclude Slides.pptx",
    "match_threshold": 0.80,
    "exclusion_scope": ["template", "branding"]
  }
}
```

## Registry Entry

```yaml
service_id: slide_design_match
type: rule
version: 1
execution_mode: sequential
dependency_stage: extraction
requires: [pptx, reference_template_ppt]
enabled_by_default: false
```

## Failure Behaviour

- Reference PPT missing or unreadable → `match_filter_status: unavailable`; zero exclusions; continue
- Partial parse → match only readable slides; log which were skipped

## Testing

- Test: exact match → slide excluded from design agents
- Test: partial match (score 0.70 < threshold 0.85) → not excluded
- Test: no reference PPT → service skipped; all slides reviewed
- Test: unreadable reference PPT → graceful degradation; pipeline continues

## Audit Trail

Every matched slide is recorded in `slide_exclusions` with `reference_template_id` and match score.
See: [../architecture/exclusions.md](../architecture/exclusions.md)

## UI

- "Design Matched" badge on excluded slides
- Tooltip: "This slide matches the approved reference template. Design agents were not applied."
- Content findings still appear for matched slides

## Related Documents

- See: [../architecture/05-review-profiles.md](../architecture/05-review-profiles.md) for profile config
- See: [../architecture/exclusions.md](../architecture/exclusions.md) for exclusion audit trail

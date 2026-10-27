# Review Profiles

## Purpose

A Review Profile makes the same PPT produce different reviews for different audiences and purposes
without any code changes. Profiles are data — stored, versioned, and editable from the Admin UI.

## Profile Schema

```json
{
  "review_profile": "customer_presentation",
  "version": 2,
  "customer": "ABC Corporation",
  "audience": "CTO + Business Leadership",
  "objective": "Get approval for proposed solution",
  "industry": "Banking",
  "presentation_level": "executive",
  "agents": [
    { "id": "template",          "enabled": true  },
    { "id": "branding",          "enabled": true  },
    { "id": "security",          "enabled": true  },
    { "id": "accessibility",     "enabled": true  },
    { "id": "content",           "enabled": true  },
    { "id": "story",             "enabled": true  },
    { "id": "customer_focus",    "enabled": true  },
    { "id": "proposal_context",  "enabled": true  },
    { "id": "cio_lens",          "enabled": true  },
    { "id": "critic",            "enabled": true  },
    { "id": "architecture",      "enabled": false }
  ],
  "slide_design_match": {
    "enabled": true,
    "reference_template_id": "infobeans-master-v3",
    "match_threshold": 0.85,
    "exclusion_scope": ["template", "branding"]
  },
  "prompt_overrides": {
    "customer_focus": 7,
    "cio_lens": 3
  }
}
```

## Rules

- Never hardcode a profile in Python. Profiles are data.
- `prompt_overrides` allows a profile to activate a specific prompt version for an agent
  (overrides the global active version for that agent).
- Profiles support both **Run All** (full plan from profile) and **Run Selected** (subset that the
  orchestrator resolves against dependencies).
- Adding a new agent: update relevant profiles with `"enabled": true/false`.

## Common Profiles

| Profile | Purpose | Proposal Agent | CIO Lens |
|---------|---------|---------------|----------|
| `customer_presentation` | Customer-facing executive deck | enabled | enabled |
| `internal_review` | Internal team review | disabled | disabled |
| `proposal_submission` | Full proposal review | enabled | enabled |
| `brand_audit` | Brand compliance only | disabled | disabled |

## Related Documents

- See: [03-agent-registry.md](03-agent-registry.md) for agent definitions
- See: [02-agent-dag.md](02-agent-dag.md) for execution model
- See: [../agents/slide-design-match.md](../agents/slide-design-match.md) for design match config

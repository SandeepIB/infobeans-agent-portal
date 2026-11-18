# Reproducibility — NOW

## Purpose

A review must record enough information to reproduce its result. "Why did this deck score 72 last
month but 86 today?" must always be answerable.

## Reproducibility Record

Every `review_run` stores:

```json
{
  "review_run_id": "rrn_abc123",
  "ppt_artifact_id": "ppt_xyz",
  "ppt_version": "sha256:abc...",

  "review_profile_id": "customer_presentation",
  "review_profile_version": 3,

  "proposal_context_id": "ctx_def",
  "proposal_context_version": 1,

  "reference_template_id": "infobeans-master-v3",
  "reference_template_version": 2,

  "agent_versions": {
    "content": 2,
    "story": 1,
    "customer_focus": 3,
    "cio_lens": 4,
    "proposal_context": 1,
    "critic": 2,
    "fix": 1
  },

  "prompt_versions": {
    "content": 5,
    "story": 3,
    "customer_focus": 7,
    "cio_lens": 2,
    "proposal_context": 3,
    "critic": 1
  },

  "rule_versions": {
    "branding": 3,
    "template": 2,
    "security": 1,
    "accessibility": 2
  },

  "model_routing": {
    "provider": "gateway",
    "model": "gpt-4o",
    "temperature": 0.2
  },

  "schema_version": 2,

  "slide_exclusions": [
    { "slide": 3, "reason": "slide_design_match", "excluded_agents": ["template", "branding"] }
  ],

  "started_at": "2025-01-15T10:30:00Z",
  "completed_at": "2025-01-15T10:31:45Z"
}
```

## What Changes the Result

A review result changes if ANY of the following change:

- The PPT content
- The Review Profile (agent list, weights, thresholds)
- The Proposal Context
- The Reference Template
- Any agent version
- Any prompt version
- Any rule version
- The model or provider
- Temperature or other model config

## Answering "Why did the score change?"

```
Old run: prompt_version.content = 5, score = 72
New run: prompt_version.content = 6, score = 86

Difference: content prompt version changed from 5 to 6
Compare via Admin UI → Prompt Version Compare
```

## Reproducing a Result

Given a `review_run_id`:
1. Load the reproducibility record
2. Restore the exact PPT version
3. Restore the exact Review Profile version
4. Restore the exact prompt versions and rule versions
5. Use the same provider + model + temperature
6. Apply the same exclusions

The system does not guarantee bit-for-bit identical LLM outputs (LLMs are non-deterministic at
temperature > 0), but the inputs are guaranteed reproducible.

For deterministic reproduction, set `temperature = 0.0` in the reproducibility record.

## Related Documents

- See: [10-versioning-audit.md](10-versioning-audit.md) for versioning scheme
- See: [08-data-flow.md](08-data-flow.md) for data lineage
- See: [exclusions.md](exclusions.md) for exclusion audit trail

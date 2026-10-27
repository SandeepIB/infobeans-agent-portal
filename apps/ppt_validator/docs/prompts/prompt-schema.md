# Prompt Schema

## YAML Seed Format

```yaml
agent_id: content_agent
version: 1
status: active                  # active | draft | deprecated
description: "Initial content review prompt"
created_by: "system"

system_role: |
  You are the Content Review Agent for the InfoBeans PPT Review Platform.
  Your job is to evaluate slide content quality, clarity, and relevance.
  Return only the structured Agent Contract JSON. Do not add commentary.

user_template: |
  Review the following slide content extracted from a PowerPoint presentation.

  Slide number: {{slide_number}}
  Slide title: {{slide_title}}
  Slide content: {{slide_content}}
  Review profile: {{review_profile}}

  Evaluate and return findings as the Agent Contract JSON.

output_schema:
  type: object
  required: [agent_id, status, score, findings, summary]
  properties:
    agent_id:   { type: string }
    status:     { type: string, enum: [completed, failed, skipped] }
    score:      { type: integer, minimum: 0, maximum: 100 }
    findings:   { type: array }
    summary:    { type: string }

few_shot_examples: []

notes: "Baseline prompt. Tune temperature and few-shots before v2."
```

## DB Tables

```sql
CREATE TABLE IF NOT EXISTS prompt_versions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id            TEXT NOT NULL,
    version             INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft',
    system_role         TEXT NOT NULL,
    user_template       TEXT NOT NULL,
    output_schema       TEXT NOT NULL,   -- JSON string
    few_shot_examples   TEXT,            -- JSON string, nullable
    description         TEXT,
    created_by          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, version)
);

CREATE TABLE IF NOT EXISTS prompt_activations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id            TEXT NOT NULL,
    prompt_version_id   INTEGER NOT NULL REFERENCES prompt_versions(id),
    review_profile      TEXT,            -- NULL = global default
    activated_by        TEXT,
    activated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Both are additive migrations — `CREATE TABLE IF NOT EXISTS`, idempotent.

## Prompt Variable Catalogue

Every `{{variable}}` used in any prompt template must be documented here.

| Variable | Supplied by | Used in agents |
|---------|------------|----------------|
| `slide_number` | PPT extraction | content, story, customer, proposal |
| `slide_title` | PPT extraction | content, story, customer, proposal |
| `slide_content` | PPT extraction | content, customer |
| `slide_summary` | Content Agent | story, cio_lens |
| `deck_summary` | Content Agent output | cio_lens, critic |
| `review_profile` | Review Request | all agents |
| `audience` | Review Profile | customer_focus, cio_lens, proposal |
| `industry` | Review Profile | customer_focus, cio_lens |
| `proposal_context` | Review Request (optional) | proposal_context |
| `all_findings` | Aggregator | critic |
| `finding_json` | Individual finding | fix_agent |

## Errors

| Error | When raised |
|-------|------------|
| `PromptNotFoundError` | No active version for agent_id |
| `PromptRenderError` | Required `{{variable}}` missing from variables dict |

## Related Documents

- See: [prompt-lifecycle.md](prompt-lifecycle.md) for lifecycle management
- See: [../architecture/10-versioning-audit.md](../architecture/10-versioning-audit.md) for audit trail

# Versioning and Audit Trail

## Purpose

Every meaningful artifact carries a version. Every operation is logged. This makes "why did this
deck score 72 last month but 86 today?" always answerable.

## Versioned Artifacts

| Artifact | Version scheme | Immutable once? |
|---------|----------------|----------------|
| Prompt version | integer per agent_id | Yes (once active) |
| Rule set version | integer per domain | Yes (once loaded) |
| Agent version | integer per agent_id | Yes |
| Review Profile | integer per profile_id | Yes |
| PPT upload | UUID + upload timestamp | Yes |
| Proposal Context | integer per context_id | Yes |
| Reference Template | integer per template_id | Yes |

## Audit Tables

### `agent_runs`

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id    TEXT NOT NULL,
    agent_id         TEXT NOT NULL,
    agent_version    INTEGER NOT NULL,
    prompt_version_id INTEGER,          -- null for rule-only agents
    rule_version_id  INTEGER,           -- null for llm-only agents
    status           TEXT NOT NULL,     -- completed | failed | skipped
    score            INTEGER,
    findings_json    TEXT NOT NULL,
    summary          TEXT,
    started_at       DATETIME,
    completed_at     DATETIME,
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    cost_usd         REAL
);
```

### `llm_requests`

```sql
CREATE TABLE IF NOT EXISTS llm_requests (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id      INTEGER NOT NULL,
    prompt_version_id INTEGER,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_hash       TEXT NOT NULL,
    input_tokens      INTEGER,
    output_tokens     INTEGER,
    cached_tokens     INTEGER,
    latency_ms        INTEGER,
    status            TEXT NOT NULL,
    error_message     TEXT,
    cost_usd          REAL,
    called_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `fix_operations`

```sql
CREATE TABLE IF NOT EXISTS fix_operations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id    TEXT NOT NULL,
    finding_id       TEXT NOT NULL,
    slide_number     INTEGER,
    change_type      TEXT NOT NULL,
    before_value     TEXT,
    after_value      TEXT,
    applied_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `audit_logs`

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type       TEXT NOT NULL,
    entity_type      TEXT NOT NULL,
    entity_id        TEXT NOT NULL,
    actor            TEXT,
    payload_json     TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Review Run Audit Trail

Every review run captures:

```json
{
  "review_run_id": "rrn_abc123",
  "ppt_version_id": "...",
  "review_profile_id": "...",
  "review_profile_version": 3,
  "proposal_context_id": "...",
  "proposal_context_version": 1,
  "reference_template_id": "...",
  "reference_template_version": 2,
  "agent_versions": { "content": 2, "story": 1, "cio_lens": 4 },
  "prompt_versions": { "content": 5, "story": 3, "cio_lens": 2 },
  "rule_versions": { "branding": 3, "template": 2 },
  "provider": "gateway",
  "model": "gpt-4o",
  "schema_version": 2
}
```

## Rules

- All migrations are `CREATE TABLE IF NOT EXISTS` — idempotent, additive.
- Never drop or alter existing audit tables.
- Versions are monotonically increasing integers. Never reuse a version number.
- A prompt version is immutable once its status moves from `draft` to `active`.

## Related Documents

- See: [reproducibility.md](reproducibility.md) for reproducing a review result
- See: [../development/database.md](../development/database.md) for migration rules

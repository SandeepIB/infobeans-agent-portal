-- Migration 001: Core v2 tables
-- Additive, idempotent

CREATE TABLE IF NOT EXISTS review_runs (
    id                      TEXT PRIMARY KEY,  -- UUID
    status                  TEXT NOT NULL DEFAULT 'queued',
    review_profile          TEXT NOT NULL,
    ppt_filename            TEXT NOT NULL,
    ppt_hash                TEXT NOT NULL,
    ppt_path                TEXT,
    reference_template_id   TEXT,
    proposal_context_id     TEXT,
    exclude_slides          TEXT,              -- JSON array of slide numbers
    score                   INTEGER,
    readiness               TEXT,
    blocked_reason          TEXT,
    created_by              TEXT,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at            DATETIME,
    cancelled_at            DATETIME
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id       TEXT NOT NULL REFERENCES review_runs(id),
    agent_id            TEXT NOT NULL,
    agent_version       INTEGER NOT NULL DEFAULT 1,
    status              TEXT NOT NULL,
    score               INTEGER,
    summary             TEXT,
    findings_json       TEXT,
    prompt_version_id   INTEGER,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    latency_ms          INTEGER DEFAULT 0,
    reused_from_run_id  TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS llm_requests (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id        INTEGER REFERENCES agent_runs(id),
    review_run_id       TEXT REFERENCES review_runs(id),
    provider            TEXT NOT NULL,
    model               TEXT NOT NULL,
    prompt_hash         TEXT NOT NULL,
    prompt_version_id   INTEGER,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    cached_tokens       INTEGER DEFAULT 0,
    latency_ms          INTEGER DEFAULT 0,
    cost_usd            REAL DEFAULT 0,
    status              TEXT NOT NULL,
    error_message       TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id            TEXT NOT NULL,
    version             INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft',
    system_role         TEXT NOT NULL,
    user_template       TEXT NOT NULL,
    output_schema       TEXT NOT NULL,
    few_shot_examples   TEXT,
    description         TEXT,
    created_by          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, version)
);

CREATE TABLE IF NOT EXISTS prompt_activations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id            TEXT NOT NULL,
    prompt_version_id   INTEGER NOT NULL REFERENCES prompt_versions(id),
    review_profile      TEXT,
    activated_by        TEXT,
    activated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rule_versions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    domain              TEXT NOT NULL,
    version             INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft',
    rules_json          TEXT NOT NULL,
    description         TEXT,
    created_by          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(domain, version)
);

CREATE TABLE IF NOT EXISTS reference_templates (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    version             INTEGER NOT NULL DEFAULT 1,
    file_path           TEXT NOT NULL,
    file_hash           TEXT NOT NULL,
    created_by          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proposal_contexts (
    id                  TEXT PRIMARY KEY,
    version             INTEGER NOT NULL DEFAULT 1,
    client              TEXT,
    context_json        TEXT NOT NULL,
    source_type         TEXT,
    source_filename     TEXT,
    created_by          TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key           TEXT PRIMARY KEY,
    provider            TEXT NOT NULL,
    model               TEXT NOT NULL,
    prompt_version_id   INTEGER,
    response_json       TEXT NOT NULL,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at          DATETIME,
    hit_count           INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS human_feedback (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id       TEXT NOT NULL REFERENCES review_runs(id),
    agent_run_id        INTEGER REFERENCES agent_runs(id),
    finding_index       INTEGER,
    feedback_type       TEXT NOT NULL,  -- correct|false_positive|false_negative|accepted|rejected
    reviewer            TEXT,
    notes               TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trulens_evaluations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id        INTEGER NOT NULL REFERENCES agent_runs(id),
    prompt_version_id   INTEGER NOT NULL,
    metric              TEXT NOT NULL,
    score               REAL,
    explanation         TEXT,
    status              TEXT NOT NULL DEFAULT 'completed',
    evaluated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type          TEXT NOT NULL,
    entity_type         TEXT,
    entity_id           TEXT,
    actor               TEXT,
    details_json        TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_review_run ON agent_runs(review_run_id);
CREATE INDEX IF NOT EXISTS idx_llm_requests_review_run ON llm_requests(review_run_id);
CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_human_feedback_run ON human_feedback(review_run_id);

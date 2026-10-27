-- Migration 001: Core v2 tables (MySQL 8.0+)
-- Additive, idempotent

CREATE TABLE IF NOT EXISTS review_runs (
    id                      VARCHAR(36)   NOT NULL PRIMARY KEY,
    run_id                  VARCHAR(36),
    status                  VARCHAR(50)   NOT NULL DEFAULT 'queued',
    review_profile          VARCHAR(500)  NOT NULL DEFAULT '',
    profile_json            LONGTEXT,
    ppt_filename            VARCHAR(500)  NOT NULL DEFAULT '',
    filename                VARCHAR(500),
    ppt_hash                VARCHAR(64)   NOT NULL DEFAULT '',
    ppt_path                VARCHAR(1000),
    reference_template_id   VARCHAR(36),
    proposal_context_id     VARCHAR(36),
    exclude_slides          TEXT,
    score                   INT,
    readiness               VARCHAR(50),
    blocked_reason          TEXT,
    result_json             LONGTEXT,
    created_by              VARCHAR(255),
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at              DATETIME,
    completed_at            DATETIME,
    cancelled_at            DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_runs (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    review_run_id       VARCHAR(36)  NOT NULL,
    agent_id            VARCHAR(100) NOT NULL,
    agent_version       INT          NOT NULL DEFAULT 1,
    status              VARCHAR(50)  NOT NULL,
    score               INT,
    summary             TEXT,
    findings_json       LONGTEXT,
    prompt_version_id   INT,
    input_tokens        INT          DEFAULT 0,
    output_tokens       INT          DEFAULT 0,
    latency_ms          INT          DEFAULT 0,
    reused_from_run_id  VARCHAR(36),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (review_run_id) REFERENCES review_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS llm_requests (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agent_run_id        INT,
    review_run_id       VARCHAR(36),
    agent_id            VARCHAR(100),
    provider            VARCHAR(100) NOT NULL,
    model               VARCHAR(200) NOT NULL,
    prompt_hash         VARCHAR(64)  NOT NULL,
    prompt_version_id   INT,
    input_tokens        INT          DEFAULT 0,
    output_tokens       INT          DEFAULT 0,
    cached_tokens       INT          DEFAULT 0,
    latency_ms          INT          DEFAULT 0,
    cost_usd            DECIMAL(10,6) DEFAULT 0,
    status              VARCHAR(50)  NOT NULL,
    error_message       TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS prompt_versions (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agent_id            VARCHAR(100) NOT NULL,
    version             INT          NOT NULL DEFAULT 1,
    version_tag         VARCHAR(100),
    status              VARCHAR(50)  NOT NULL DEFAULT 'draft',
    system_role         TEXT,
    system_prompt       TEXT,
    user_template       LONGTEXT,
    output_schema       LONGTEXT,
    few_shot_examples   LONGTEXT,
    description         TEXT,
    created_by          VARCHAR(255),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_agent_version (agent_id, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS prompt_activations (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agent_id            VARCHAR(100) NOT NULL,
    prompt_version_id   INT          NOT NULL,
    is_active           TINYINT      DEFAULT 0,
    review_profile      VARCHAR(200),
    activated_by        VARCHAR(255),
    activated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_version_id) REFERENCES prompt_versions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rule_versions (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    domain              VARCHAR(100) NOT NULL,
    version             INT          NOT NULL DEFAULT 1,
    rule_id             VARCHAR(200),
    status              VARCHAR(50)  NOT NULL DEFAULT 'draft',
    rules_json          LONGTEXT,
    rule_json           LONGTEXT,
    is_active           TINYINT      DEFAULT 0,
    description         TEXT,
    created_by          VARCHAR(255),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_domain_version (domain, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reference_templates (
    id                  VARCHAR(36)   NOT NULL PRIMARY KEY,
    name                VARCHAR(500)  NOT NULL,
    version             INT           NOT NULL DEFAULT 1,
    file_path           VARCHAR(1000) NOT NULL,
    file_hash           VARCHAR(64)   NOT NULL,
    created_by          VARCHAR(255),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS proposal_contexts (
    id                  VARCHAR(36)  NOT NULL PRIMARY KEY,
    version             INT          NOT NULL DEFAULT 1,
    client              VARCHAR(500),
    context_json        LONGTEXT     NOT NULL,
    source_type         VARCHAR(100),
    source_filename     VARCHAR(500),
    created_by          VARCHAR(255),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key           VARCHAR(64)  NOT NULL PRIMARY KEY,
    provider            VARCHAR(100) NOT NULL,
    model               VARCHAR(200) NOT NULL,
    prompt_version_id   INT,
    response_json       LONGTEXT     NOT NULL,
    input_tokens        INT          DEFAULT 0,
    output_tokens       INT          DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at          DATETIME,
    hit_count           INT          DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS human_feedback (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    review_run_id       VARCHAR(36)  NOT NULL,
    agent_run_id        INT,
    finding_index       INT,
    feedback_type       VARCHAR(100) NOT NULL,
    reviewer            VARCHAR(255),
    notes               TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (review_run_id) REFERENCES review_runs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS trulens_evaluations (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agent_run_id        INT          NOT NULL,
    prompt_version_id   INT          NOT NULL,
    metric              VARCHAR(200) NOT NULL,
    score               DECIMAL(5,4),
    explanation         TEXT,
    status              VARCHAR(50)  NOT NULL DEFAULT 'completed',
    evaluated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
    id                  INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    event_type          VARCHAR(200) NOT NULL,
    entity_type         VARCHAR(100),
    entity_id           VARCHAR(255),
    actor               VARCHAR(255),
    details_json        LONGTEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_agent_runs_review_run ON agent_runs(review_run_id);
CREATE INDEX idx_llm_requests_review_run ON llm_requests(review_run_id);
CREATE INDEX idx_llm_cache_expires ON llm_cache(expires_at);
CREATE INDEX idx_human_feedback_run ON human_feedback(review_run_id);

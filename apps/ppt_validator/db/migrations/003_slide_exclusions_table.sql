-- Migration 003: Slide Exclusions Table
-- Additive, idempotent

CREATE TABLE IF NOT EXISTS slide_exclusions (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    review_run_id          TEXT NOT NULL,
    slide_number           INTEGER NOT NULL,
    excluded_agents        TEXT NOT NULL,
    reason                 TEXT NOT NULL,
    detail                 TEXT,
    excluded_by            TEXT NOT NULL DEFAULT 'system',
    reference_template_id  TEXT,
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_slide_exclusions_run ON slide_exclusions(review_run_id);

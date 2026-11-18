-- Migration 003: Slide Exclusions Table for MySQL
-- Additive, idempotent

CREATE TABLE IF NOT EXISTS slide_exclusions (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    review_run_id          VARCHAR(255) NOT NULL,
    slide_number           INT NOT NULL,
    excluded_agents        TEXT NOT NULL,
    reason                 VARCHAR(255) NOT NULL,
    detail                 TEXT,
    excluded_by            VARCHAR(255) NOT NULL DEFAULT 'system',
    reference_template_id  VARCHAR(255),
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_slide_exclusions_run ON slide_exclusions(review_run_id);

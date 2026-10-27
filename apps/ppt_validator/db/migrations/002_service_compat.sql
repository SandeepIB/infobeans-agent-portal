-- Migration 002: Service-compatible table aliases
-- Adds columns/tables that match the services layer exactly.
-- Additive, idempotent.

-- review_runs: add missing columns used by ReviewService
ALTER TABLE review_runs ADD COLUMN run_id TEXT;
ALTER TABLE review_runs ADD COLUMN filename TEXT;
ALTER TABLE review_runs ADD COLUMN profile_json TEXT;
ALTER TABLE review_runs ADD COLUMN result_json TEXT;
ALTER TABLE review_runs ADD COLUMN started_at DATETIME;

-- prompt_versions: add system_prompt and version_tag columns
ALTER TABLE prompt_versions ADD COLUMN system_prompt TEXT;
ALTER TABLE prompt_versions ADD COLUMN version_tag TEXT;

-- prompt_activations: add is_active column
ALTER TABLE prompt_activations ADD COLUMN is_active INTEGER DEFAULT 0;

-- rule_versions: add rule_id, rule_json, is_active columns
ALTER TABLE rule_versions ADD COLUMN rule_id TEXT;
ALTER TABLE rule_versions ADD COLUMN rule_json TEXT;
ALTER TABLE rule_versions ADD COLUMN is_active INTEGER DEFAULT 0;

-- llm_requests: add agent_id column (services insert by agent_id directly)
ALTER TABLE llm_requests ADD COLUMN agent_id TEXT;

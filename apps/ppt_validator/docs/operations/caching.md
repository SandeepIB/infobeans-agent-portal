# LLM Caching — NOW

## Purpose

Avoid redundant LLM calls. Cache responses where inputs are deterministic and unchanged.
Caching directly reduces cost and latency.

## Cache Architecture

### Cache Key Components

```python
cache_key = hash({
    "provider":          "gateway",
    "model":             "gpt-4o",
    "prompt_version_id": 5,
    "schema_version":    2,
    "normalized_input_hash": sha256(normalized_slide_content),
    "context_hash":      sha256(relevant_context),
    "configuration_hash": sha256(temperature + max_tokens + ...),
})
```

All components are included to prevent stale or wrong results.

### Cache Scopes

| Scope | Key | Use case |
|-------|-----|---------|
| Exact request | Full cache key | Identical prompt + input on re-review |
| Slide-level | Slide content hash | Same slide reused across multiple reviews |
| Agent-level | Agent + full context hash | Full agent result for unchanged PPT section |
| Evaluation | Evaluation input hash | TruLens eval results for same input |
| Preprocessing | Input + rule hash | Deterministic rule-check results |

### Cacheability by Agent

| Agent | Cacheability |
|-------|-------------|
| template (rule) | `full` |
| branding (rule) | `full` |
| content (llm) | `slide_level` |
| story (llm) | `full` (depends on full slide sequence) |
| customer_focus (llm) | `full` |
| proposal_context (llm) | `full` |
| cio_lens (llm) | `full` (depends on deck summary) |
| critic (llm) | `none` (always reruns if anything changed) |
| fix (hybrid) | `none` |

### What Is NOT Cached

- Requests where inputs are intentionally nondeterministic (if explicitly configured)
- Critic agent results (always reruns)
- Fix agent results (always reruns)

## Cache Storage

Phase 1: SQLite table `llm_cache`.
Future: Redis or external cache store.

```sql
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key         TEXT PRIMARY KEY,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_version_id INTEGER,
    response_json     TEXT NOT NULL,
    input_tokens      INTEGER,
    output_tokens     INTEGER,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at        DATETIME,
    hit_count         INTEGER DEFAULT 0
);
```

## Cache Metrics

Every cache lookup records:

| Metric | Description |
|--------|-------------|
| `cache_hit` | Boolean: was result served from cache? |
| `cache_key` | Key used for lookup |
| `tokens_saved` | Input + output tokens saved (on hit) |
| `cost_saved` | Estimated cost saved (on hit) |
| `cache_hit_rate` | % of all LLM calls served from cache |

## Invalidation

A cache entry is invalidated when:
- The prompt version changes (different `prompt_version_id`)
- The input content changes (different `normalized_input_hash`)
- The model or provider changes
- The entry expires (configurable TTL, default: 24 hours)

Invalidation is automatic via cache key — no explicit invalidation needed.

## Usage in Agent Code

```python
# CachingLLMProvider wraps any LLMProvider with caching
class CachingLLMProvider(LLMProvider):
    def complete(self, prompt, schema=None, **kwargs):
        key = self._cache_key(prompt, schema, kwargs)
        if result := self.cache.get(key):
            self.metrics.record_hit(key, result.tokens)
            return result.response
        result = self.inner.complete(prompt, schema, **kwargs)
        self.cache.set(key, result)
        return result.response
```

Agent code does not need to know about caching — it is transparent.

## Incremental Re-review and Cache

When an agent result is reused from a prior run (not a cache hit but a stored result):
- The result is explicitly marked `reused_from_run_id` in the new review
- It is NOT a cache hit — it is a prior run result

See: [../architecture/incremental-review.md](../architecture/incremental-review.md)

## Related Documents

- See: [cost-governance.md](cost-governance.md) for cost savings from caching
- See: [../architecture/incremental-review.md](../architecture/incremental-review.md) for re-review reuse
- See: [../architecture/context-optimization.md](../architecture/context-optimization.md) for context reduction

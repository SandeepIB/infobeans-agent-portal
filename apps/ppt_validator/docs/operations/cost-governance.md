# Cost Governance — NOW

## Purpose

Enforce token and cost budgets at every level. Prevent uncontrolled LLM spend.
Every LLM call is tracked. Budgets are checked before execution.

## CostGovernanceService

```python
class CostGovernanceService:
    def estimate(self, agent_id: str, context: dict) -> CostEstimate:
        """Estimate tokens and cost before making the LLM call."""

    def check_budget(
        self,
        review_run_id: str,
        agent_id: str,
        estimated_tokens: int,
    ) -> BudgetCheckResult:
        """Return OK or EXCEEDED. Agents must check before calling LLM."""

    def record_actual(
        self,
        review_run_id: str,
        agent_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int,
        cost_usd: float,
    ) -> None:
        """Record actual cost after LLM call completes."""

    def get_run_summary(self, review_run_id: str) -> CostSummary:
        """Return cost breakdown for a review run."""
```

## Budget Levels

| Level | Enforcement | Configuration |
|-------|------------|---------------|
| Per-request | Hard limit | `MAX_TOKENS_PER_REQUEST` |
| Per-agent | Soft warning + hard limit | `MAX_TOKENS_PER_AGENT_{AGENT_ID}` |
| Per-review | Hard limit | `MAX_TOKENS_PER_REVIEW` |
| Per-project | Soft warning | `MAX_TOKENS_PER_PROJECT_DAILY` |
| Daily | Soft warning + hard limit | `MAX_COST_USD_DAILY` |
| Monthly | Soft warning + hard limit | `MAX_COST_USD_MONTHLY` |

```dotenv
MAX_TOKENS_PER_REQUEST=8192
MAX_TOKENS_PER_REVIEW=50000
MAX_COST_USD_DAILY=20.00
MAX_COST_USD_MONTHLY=400.00
```

## Budget Check Flow

```
Review Request
     │
CostGovernanceService.estimate(all_agents)
     │
Estimated tokens: 12,400
Estimated cost: $0.62
     │
Budget check:
  - Per-review: 12,400 < 50,000 ✓
  - Daily remaining: $8.20 > $0.62 ✓
     │
Orchestrator proceeds
     │
Per-agent budget check before each LLM call
     │
Actual cost recorded after each call
```

## Cost Tracking Metrics

All tracked in `llm_requests` and `cost_tracking` tables:

| Metric | Description |
|--------|-------------|
| `cost_per_slide` | Average cost to review one slide |
| `cost_per_review` | Total cost per review run |
| `cost_per_agent` | Cost breakdown by agent |
| `cost_per_prompt_version` | Cost tracked by prompt version |
| `cost_per_model` | Cost comparison across models |
| `cache_hit_rate` | % of LLM calls served from cache |
| `tokens_saved_by_cache` | Tokens saved by cache hits |
| `cost_saved_by_cache` | Cost saved by cache hits |

## Budget Exceeded Handling

| Budget | On exceed |
|--------|----------|
| Per-request | Reject; raise `BudgetExceededError` |
| Per-agent | Skip agent; log `status: budget_exceeded`; continue with other agents |
| Per-review | Stop remaining agents; return partial results with warning |
| Daily | Block new reviews; alert admin |
| Monthly | Block new reviews; alert admin |

## Dashboard Metrics

The Admin UI exposes a Cost Dashboard:

| View | Content |
|------|---------|
| Daily spend | Cost per day, trend, alert threshold |
| Per-review breakdown | Cost per agent for any review run |
| Model comparison | Cost vs quality for different models |
| Cache efficiency | Cache hit rate, cost saved |
| Budget utilization | Daily/monthly budget consumed % |

## Related Documents

- See: [../architecture/context-optimization.md](../architecture/context-optimization.md) for reducing token usage
- See: [../operations/caching.md](../operations/caching.md) for cache-based cost savings
- See: [../architecture/model-routing.md](../architecture/model-routing.md) for model cost optimization
- See: [../architecture/execution-controls.md](../architecture/execution-controls.md) for concurrency

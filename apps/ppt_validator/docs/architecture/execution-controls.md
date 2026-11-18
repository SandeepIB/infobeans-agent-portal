# Execution Controls — NOW

## Purpose

Prevent uncontrolled parallel LLM calls, runaway costs, and cascading provider failures.

## Concurrency Limits

```dotenv
# Maximum concurrent LLM calls across all agents in one review
MAX_CONCURRENT_LLM_CALLS=4

# Maximum concurrent reviews (per instance)
MAX_CONCURRENT_REVIEWS=2

# Per-provider concurrency limit
GATEWAY_MAX_CONCURRENT=4
```

The orchestrator enforces `MAX_CONCURRENT_LLM_CALLS` using a semaphore.
Parallel agents that would exceed this limit are queued.

## Rate Limiting

```dotenv
# Rate limit per provider (requests per minute)
GATEWAY_RATE_LIMIT_RPM=60
GROQ_RATE_LIMIT_RPM=30
```

`RateLimiter` enforces RPM limits using a token-bucket algorithm per provider.

## Timeout

```dotenv
# Per-agent LLM call timeout
LLM_CALL_TIMEOUT_SECONDS=60

# Per-agent total timeout (including retries)
AGENT_TIMEOUT_SECONDS=180

# Per-review total timeout
REVIEW_TIMEOUT_SECONDS=900
```

On timeout: agent is marked `status: timeout`; pipeline continues without that agent's findings.

## Retry with Exponential Backoff

```
Attempt 1 → wait 2s → Attempt 2 → wait 4s → Attempt 3 → wait 8s → Fail
```

Configuration: `LLM_MAX_RETRIES=3`, `LLM_RETRY_BACKOFF_SECONDS=2`.

## Circuit Breaker

```
Trips after: 5 consecutive failures to same provider
Stays open: 60 seconds
Recovery: test with 1 request; if success, close circuit
```

On open circuit: skip provider; use fallback if configured (see [model-routing.md](model-routing.md)).

## Request Queue

When `MAX_CONCURRENT_LLM_CALLS` is reached, new agent calls are queued (not dropped).
Queue depth limit: `MAX_QUEUE_DEPTH=20`. Requests beyond this return `status: queue_full`.

## Cancellation

Review runs can be cancelled by the user mid-execution.
The orchestrator propagates cancellation to all running agents.
Partial results are logged; audit trail records cancellation.

## Budget-Aware Execution

Before each agent call:
1. `CostGovernanceService.check_budget(review_run_id, agent_id, estimated_tokens)`
2. If budget exceeded: skip agent; log `status: budget_exceeded`
3. If within budget: proceed

See: [../operations/cost-governance.md](../operations/cost-governance.md)

## Related Documents

- See: [model-routing.md](model-routing.md) for provider fallback
- See: [11-failure-recovery.md](11-failure-recovery.md) for failure modes
- See: [../operations/cost-governance.md](../operations/cost-governance.md) for budget controls

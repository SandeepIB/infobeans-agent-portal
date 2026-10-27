# Failure Recovery

## Purpose

Define how the system handles failures — at the agent level, provider level, and infrastructure level.

## Agent Failure Modes

| Failure | Handling |
|---------|---------|
| Agent raises exception | Log `agent_run.status = failed`; continue with other agents; mark that agent's findings as unavailable |
| Agent returns invalid contract | Reject and log; do not propagate partial data; mark agent failed |
| Agent times out | Cancel; log timeout; continue pipeline |
| All parallel agents fail | Escalate to BLOCKED with error finding |

## LLM Provider Failure Modes

| Failure | Handling |
|---------|---------|
| Provider unreachable | Retry with exponential backoff (3 retries, 2s base) |
| Rate limit hit | Queue and retry after rate-limit window |
| Structured output parse failure | Retry prompt up to `LLM_MAX_RETRIES`; raise `LLMStructuredOutputError` if all fail |
| Provider fully down | Circuit breaker → fail fast; try provider fallback if configured |
| Budget exceeded | Abort request; return `status: budget_exceeded` |

## Observability Failure Modes

| Failure | Handling |
|---------|---------|
| LangSmith unreachable | Log WARNING; continue pipeline; no data loss |
| TruLens eval job fails | Log WARNING; mark evaluation row `status: failed`; review run unaffected |

## Renderer Failure Modes

| Failure | Handling |
|---------|---------|
| LibreOffice not installed | `UnavailableRenderer`; Visual Agent emits INFO finding; pipeline continues |
| LibreOffice crashes | Log; emit WARNING finding; pipeline continues |

## Slide Design Match Failure Modes

| Failure | Handling |
|---------|---------|
| Reference PPT missing | Log WARNING; `match_filter_status: unavailable`; zero exclusions; pipeline continues |
| Partial parse | Match only readable slides; log which were skipped |

## Retry Configuration

```dotenv
LLM_MAX_RETRIES=3
LLM_RETRY_BACKOFF_SECONDS=2
```

Retry uses exponential backoff: 2s, 4s, 8s.

## Circuit Breaker

- Trips after N consecutive failures to same provider.
- Stays open for configurable window.
- Optional: fall back to secondary provider (see [model-routing.md](model-routing.md)).

## Related Documents

- See: [execution-controls.md](execution-controls.md) for concurrency and rate limits
- See: [model-routing.md](model-routing.md) for provider fallback
- See: [06-llm-provider.md](06-llm-provider.md) for retry configuration

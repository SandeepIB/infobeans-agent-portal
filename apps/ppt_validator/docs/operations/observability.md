# Observability — NOW

## Purpose

Provide traces, token usage, cost, latency, errors, and evaluation scores without blocking the
review pipeline. LangSmith and TruLens are side-channels — not gates.

## Tools

| Tool | Role |
|------|------|
| LangSmith | End-to-end LLM call tracing: inputs, outputs, tokens, cost, latency |
| TruLens | Prompt quality evaluation: groundedness, relevance, schema compliance |

## LangSmith Integration

### Integration Point

Tracing is added at the `LLMProvider` base class level — one decorator, all providers traced.

```python
from langsmith import traceable

class LLMProvider(ABC):
    @traceable(name="llm_complete", run_type="llm")
    def complete(self, prompt: str, schema: dict | None = None, **kwargs) -> dict:
        return self._complete(prompt, schema, **kwargs)
```

### What Is Traced

Every call through `LLMProvider.complete()`:
- `agent_id`, `prompt_version_id`, `provider`, `model`
- Rendered prompt (with PII redaction if enabled)
- Raw LLM response + parsed output (with PII redaction if enabled)
- `input_tokens`, `output_tokens`, `latency_ms`, status
- `review_run_id` — links to platform audit trail

### Configuration

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<placeholder>
LANGSMITH_PROJECT=ib-ppt-validator
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_CAPTURE_INPUTS=true
LANGSMITH_CAPTURE_OUTPUTS=true
LANGSMITH_REDACT_PII=true
```

Set `LANGSMITH_ENABLED=false` to disable all tracing with zero code changes.

## TruLens Integration

### Integration Point

```python
class ObservabilityService:
    def record_agent_run(self, agent_run: AgentRun) -> None:
        """Write to audit DB. Enqueue async TruLens eval job if enabled."""

    def evaluate_async(self, agent_run, prompt_version) -> None:
        """Run TruLens feedback functions. Never in critical path."""
```

### Configuration

```dotenv
TRULENS_ENABLED=true
TRULENS_DATABASE_URL=sqlite:///trulens.db
TRULENS_EVAL_PROVIDER=openai
TRULENS_EVAL_MODEL=gpt-4o-mini
```

## Admin UI — Observability Dashboards

| Dashboard | Content |
|-----------|---------|
| Agent Run Dashboard | All runs, scores, latency, token cost, status |
| LLM Call Explorer | LangSmith-linked trace per call |
| Prompt Eval Results | TruLens scores per prompt version per metric |
| Prompt Version Compare | Side-by-side metric scores for two prompt versions |
| Cost Dashboard | Daily/monthly spend, cache hit rate, per-agent cost |
| Alerts | Groundedness < threshold, error rate spike, latency regression |

## Failure Behaviour

| Failure | Handling |
|---------|---------|
| LangSmith unreachable | Log WARNING; continue; no data lost; no review blocked |
| TruLens eval job fails | Log WARNING; mark eval row `status: failed`; review unaffected |
| `LANGSMITH_ENABLED=false` | Wrapper is a no-op; no tracing |
| `TRULENS_ENABLED=false` | No eval jobs enqueued |

## Critical Path Rule

Observability must never block the review pipeline. LangSmith and TruLens write to:
- External services (LangSmith)
- A separate DB (TruLens)

Neither writes to the `agent_runs` or `findings` tables. They are read-only consumers of the
audit trail.

## Related Documents

- See: [../prompts/prompt-security.md](../prompts/prompt-security.md) for PII redaction
- See: [cost-governance.md](cost-governance.md) for cost metrics
- See: [../evaluation/evaluation.md](../evaluation/evaluation.md) for evaluation framework

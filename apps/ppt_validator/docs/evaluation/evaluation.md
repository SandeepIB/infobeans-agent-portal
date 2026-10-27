# Evaluation Framework — NOW

## Purpose

Two complementary observability and evaluation layers run alongside the platform.

| Tool | Primary role |
|------|-------------|
| **LangSmith** | Trace every LLM call: inputs, outputs, latency, token cost |
| **TruLens** | Evaluate prompt quality and LLM output correctness |

Neither is in the critical path. Both are side-channels.

## TruLens — What It Evaluates

TruLens runs asynchronous evaluation jobs against completed agent runs.

| Metric | Description |
|--------|-------------|
| `answer_relevance` | Is the finding relevant to the slide content? |
| `groundedness` | Is the finding grounded in actual slide text (not hallucinated)? |
| `context_relevance` | Is the retrieved context relevant to the prompt? |
| `coherence` | Is the finding description coherent? |
| `output_schema_compliance` | Does the output conform to the declared output schema? |
| `requirement_coverage` | Does output cover all proposal requirements? (Proposal Agent only) |
| `contradiction_detection` | Does agent correctly identify contradictions? (Proposal + Critic) |

## TruLens Integration Point

```python
class ObservabilityService:
    def record_agent_run(self, agent_run: AgentRun) -> None:
        """Write to audit DB. If TruLens enabled, enqueue async eval job."""

    def evaluate_async(self, agent_run: AgentRun, prompt_version: PromptVersion) -> None:
        """Run TruLens feedback functions. Store in trulens_evaluations table.
        Never called in the critical path — always async/background."""
```

## TruLens Evaluation Results Table

```sql
CREATE TABLE IF NOT EXISTS trulens_evaluations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_run_id        INTEGER NOT NULL,
    prompt_version_id   INTEGER NOT NULL,
    metric              TEXT NOT NULL,
    score               REAL,             -- 0.0 – 1.0
    explanation         TEXT,
    evaluated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## LangSmith — What It Traces

Every call through `LLMProvider.complete()` is wrapped in a LangSmith run:

- `agent_id`, `prompt_version_id`, `provider`, `model`
- Rendered system prompt + user message (with PII redaction if enabled)
- Raw LLM response + parsed structured output
- `input_tokens`, `output_tokens`, `latency_ms`, status
- `review_run_id` — links to platform audit trail

## Configuration

```dotenv
# LangSmith
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<placeholder>
LANGSMITH_PROJECT=ib-ppt-validator
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# TruLens
TRULENS_ENABLED=true
TRULENS_DATABASE_URL=sqlite:///trulens.db
TRULENS_EVAL_PROVIDER=openai
TRULENS_EVAL_MODEL=gpt-4o-mini
```

Set either flag to `false` to disable with zero code changes.

## Failure Behaviour

- LangSmith unreachable → log WARNING; continue; no data lost
- TruLens eval job fails → log WARNING; mark row `status: failed`; review unaffected

## Version Awareness

Every evaluation identifies:
- `dataset_version`
- `prompt_version`
- `agent_version`
- `model`
- `provider`
- `review_profile`

This allows comparison across versions.

## Related Documents

- See: [evaluation-gates.md](evaluation-gates.md) for gate thresholds
- See: [golden-dataset.md](golden-dataset.md) for evaluation inputs
- See: [../prompts/prompt-evaluation.md](../prompts/prompt-evaluation.md) for prompt evaluation flow
- See: [../operations/observability.md](../operations/observability.md) for observability configuration

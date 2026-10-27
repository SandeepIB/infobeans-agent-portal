# Prompt Evaluation — NOW

## Purpose

Define how new prompt versions are evaluated before activation. No prompt becomes active without
passing configured evaluation gates.

## Evaluation Flow

```
1. Author creates new prompt version (status: draft)
2. Author clicks "Run Evaluation" in Admin UI
3. Platform runs draft prompt against golden evaluation dataset
4. TruLens scores outputs on configured metrics
5. Scores appear in Admin UI alongside previous active version scores
6. Author compares: if new version meets gates, eligible for activation
7. Authorized user activates the version
```

## Evaluation Metrics

| Metric | Description | Applies to |
|--------|-------------|-----------|
| `answer_relevance` | Finding relevant to slide content? | All LLM agents |
| `groundedness` | Finding grounded in actual slide text (not hallucinated)? | All LLM agents |
| `context_relevance` | Context provided is relevant to the prompt? | All LLM agents |
| `coherence` | Finding description coherent and well-formed? | All LLM agents |
| `output_schema_compliance` | Output conforms to declared output schema? | All LLM agents |
| `requirement_coverage` | Agent output covers all proposal requirements? | Proposal Agent |
| `contradiction_detection` | Agent correctly identifies contradictions? | Proposal Agent, Critic |

## Evaluation Gates

A prompt version is eligible for activation only when ALL configured gates pass:

```yaml
evaluation_gates:
  groundedness:           >= 0.80
  relevance:              >= 0.75
  schema_compliance:      >= 0.95
  hallucination_rate:     <= 0.05
  critical_regression:    = 0         # no new critical false negatives
  overall_regression:     <= 0.02     # max 2% regression on existing test cases
```

See: [../evaluation/evaluation-gates.md](../evaluation/evaluation-gates.md) for gate configuration.

## Comparing Versions

The Admin UI shows side-by-side metric scores for any two prompt versions:

| Metric | V4 (current active) | V5 (draft) | Change |
|--------|---------------------|------------|--------|
| groundedness | 0.82 | 0.89 | +8.5% |
| relevance | 0.78 | 0.81 | +3.8% |
| schema_compliance | 0.98 | 0.99 | +1.0% |

## LangSmith Integration

Every evaluation call is traced in LangSmith:
- Full prompt + response for each eval input
- Token usage per eval call
- Latency per eval call
- Error rate

## Related Documents

- See: [../evaluation/evaluation-gates.md](../evaluation/evaluation-gates.md) for gate thresholds
- See: [../evaluation/golden-dataset.md](../evaluation/golden-dataset.md) for test inputs
- See: [../operations/observability.md](../operations/observability.md) for TruLens integration

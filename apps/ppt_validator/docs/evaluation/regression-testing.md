# Regression Testing — NEXT

## Purpose

Detect when a code or prompt change causes a regression in findings, scores, or evaluation metrics.
Do not run expensive regression tests for every small code change.

## Test Tiers

| Tier | Name | Runs on | Speed | Triggers |
|------|------|---------|-------|---------|
| Tier 1 | Unit tests | MockProvider, fixtures | Fast (< 2 min) | Every commit |
| Tier 2 | Integration tests | Real DB, real renderer, MockProvider | Medium (< 10 min) | Every PR |
| Tier 3 | Targeted agent tests | Golden samples, MockProvider | Medium (< 15 min) | Agent/prompt changes |
| Tier 4 | Golden evaluation | Golden dataset, real LLM | Slow (30–60 min) | Prompt activation only |
| Tier 5 | Full regression | All samples, all agents, real LLM | Very slow | Major releases |

## Choosing the Right Tier

```
Changed a single agent implementation? → Tier 1 + Tier 3 (that agent only)
Changed a prompt? → Tier 1 + Tier 4 (that prompt only)
Changed the orchestrator? → Tier 1 + Tier 2
Changed scoring weights? → Tier 1 + Tier 3
Major release? → Tier 1 through Tier 5
```

## Regression Metrics Tracked

| Metric | Description |
|--------|-------------|
| `findings_match_rate` | % of expected findings produced |
| `false_positive_rate` | Unexpected findings produced |
| `false_negative_rate` | Expected findings not produced |
| `groundedness_delta` | Change in groundedness score |
| `relevance_delta` | Change in relevance score |
| `latency_delta` | Change in agent latency |
| `token_usage_delta` | Change in token consumption |
| `cost_delta` | Change in cost per review |

## Regression Failure Thresholds

```yaml
regression_thresholds:
  findings_match_rate:    >= 0.95    # at least 95% of expected findings produced
  false_positive_rate:    <= 0.05    # max 5% new false positives
  false_negative_rate:    <= 0.02    # max 2% new false negatives
  critical_regression:    = 0         # no new critical false negatives
  groundedness_delta:     >= -0.02   # max 2% groundedness drop
  cost_delta:             <= 0.10    # max 10% cost increase without approval
```

## What Qualifies as a Regression

A regression is when a change causes:
- A CRITICAL finding to be missed (was found before, not found now)
- A false HIGH finding that wasn't there before
- Score dropping more than 10 points for a known-good sample
- Groundedness or relevance dropping below gate thresholds

## Not Running Real LLMs in Unit Tests

Tier 1 and Tier 2 must use `MockProvider`. A test that needs a real LLM must:
- Be explicitly tagged `@pytest.mark.tier4`
- Document why a real LLM is needed

```python
@pytest.mark.tier4  # only runs in full evaluation suite
def test_content_agent_on_golden_sample():
    ...
```

## Related Documents

- See: [evaluation.md](evaluation.md) for evaluation framework
- See: [evaluation-gates.md](evaluation-gates.md) for gate thresholds
- See: [../development/testing.md](../development/testing.md) for unit test patterns

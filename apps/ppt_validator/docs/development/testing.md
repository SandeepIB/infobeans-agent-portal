# Testing — NOW

## Purpose

Test architecture for the platform. Tests must be fast, cheap, and never call real LLMs.

## Core Rules

1. All unit tests use `MockProvider`. `LLM_PROVIDER=mock` in all test environments.
2. No test may call the live gateway or any real LLM API.
3. A test that requires a real LLM must be tagged `@pytest.mark.tier4`.
4. Tests run in the smallest sufficient tier for the change being made.

## Test Tiers

| Tier | Runs | What it tests | Speed |
|------|------|--------------|-------|
| 1 — Unit | `pytest tests/unit/` | Individual agents, services, MockProvider | < 2 min |
| 2 — Integration | `pytest tests/integration/` | DAG, DB, provider boundary, renderer, API | < 10 min |
| 3 — Targeted agent | `pytest tests/agents/` | Golden samples, MockProvider | < 15 min |
| 4 — Golden evaluation | `pytest tests/ -m tier4` | Real LLM, golden dataset | 30–60 min |
| 5 — Full regression | `python evaluation/run_regression.py` | All samples, all agents | Very slow |

Run Tier 1 for every change. Run Tier 2+ only when relevant.

## MockProvider

`MockProvider` returns deterministic fixtures keyed on `prompt_hash`.

```python
# Fixture format: tests/fixtures/mock_responses/<agent_id>/<prompt_hash>.json
{
  "agent_id": "content_agent",
  "status": "completed",
  "score": 82,
  "findings": [...],
  "summary": "Mock response for content agent."
}
```

### Using MockProvider in Tests

```python
import pytest
from llm.providers.mock_provider import MockProvider

@pytest.fixture
def mock_provider():
    return MockProvider(fixtures_dir="tests/fixtures/mock_responses")

def test_content_agent_returns_contract(mock_provider):
    agent = ContentAgent(
        llm_provider=mock_provider,
        prompt_service=prompt_service_with_seed_data(),
    )
    result = agent.run(context=minimal_context())
    assert result.status == "completed"
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 100
    assert all(f.action_type in {"AUTO_FIX", "HUMAN_APPROVAL", "RECOMMENDATION_ONLY"}
               for f in result.findings)
```

## Required Tests for Every New Agent

- Returns valid Agent Contract on success
- Returns `status: failed` on exception (does not propagate)
- Does not call any real LLM (MockProvider only)
- Returns `status: skipped` when required input is missing (if applicable)
- Findings all have valid `action_type`, `severity`, `confidence`

## Required Tests for Orchestrator

- Dependency ordering: agent that depends on extraction does not run before extraction
- Parallel agents run independently (one failure does not abort others)
- Budget exceeded: agent skipped, pipeline continues
- Cancelled review: in-progress agents marked cancelled

## Required Tests for Fix Agent

- Only `AUTO_FIX` findings applied
- `HUMAN_APPROVAL` findings in input are skipped
- Fix failure is logged as skipped; pipeline continues

## Required Tests for Renderer

- `LibreOfficeRenderer` — if `soffice` present
- `UnavailableRenderer` — always runs; Visual Agent emits INFO finding

## Required Tests for Slide Design Match

- Exact match → slide excluded from design agents
- Partial match below threshold → not excluded
- No reference PPT → service skipped; all slides reviewed
- Unreadable reference PPT → graceful degradation

## Fixture Guidelines

- Use small PPT fixtures (5 slides max for unit tests)
- Keep fixture PPTs anonymized
- Store golden evaluation PPTs in `evaluation/golden/samples/`

## Test Configuration

```dotenv
# .env.test
LLM_PROVIDER=mock
DATABASE_URL=sqlite:///test.db
LANGSMITH_ENABLED=false
TRULENS_ENABLED=false
```

## Related Documents

- See: [../evaluation/regression-testing.md](../evaluation/regression-testing.md) for evaluation tiers
- See: [../rules/rule-testing.md](../rules/rule-testing.md) for rule agent testing

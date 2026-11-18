# Rule Testing — NOW

## Purpose

Test rule-based agents without LLMs. Rules are deterministic — tests should be fast and cheap.

## Testing Pattern

Rule-based agents do not call LLMs. Tests do not need `MockProvider`.
They test the rule logic directly against fixture data.

```python
def test_branding_agent_color_violation():
    rule_service = RuleService(db=test_db)  # test_db with seeded v1 rules
    agent = BrandingAgent(rule_service=rule_service)

    context = {
        "design_metadata": {
            "slides": [
                {"slide": 1, "background_color": "#FF0000"}  # not in allowed palette
            ]
        }
    }

    result = agent.run(context)

    assert result.status == "completed"
    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "BRAND-001"
    assert result.findings[0].severity == "HIGH"
    assert result.findings[0].action_type == "AUTO_FIX"
```

## Test Fixtures

Use small YAML fixture files for rule sets in tests. Do not load from production DB.

```python
@pytest.fixture
def branding_rules_v1():
    return RuleSet.from_yaml("tests/fixtures/rules/branding_v1.yaml")
```

## What to Test for Each Rule

For every rule in the Rule Library, write tests covering:

| Scenario | Expected result |
|----------|----------------|
| Clear violation | Finding with correct severity and action_type |
| Clear compliance | No finding |
| Edge case (at threshold) | Document expected behaviour |
| Not-applicable scope | No finding (wrong `applies_to`) |

## Hybrid Agent Testing

Hybrid agents use rules for some checks and LLMs for others. Use `MockProvider` for LLM parts.

```python
def test_accessibility_agent_hybrid(mock_provider):
    agent = AccessibilityAgent(
        rule_service=rule_service,
        llm_provider=mock_provider,
    )
    ...
```

## Related Documents

- See: [rule-library.md](rule-library.md) for rule schema
- See: [../development/testing.md](../development/testing.md) for full testing guide

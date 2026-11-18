# Evaluation Gates — NOW

## Purpose

Define configurable gates that a prompt version must pass before it can be activated in production.
No new prompt/model configuration becomes active automatically.

## Gate Thresholds

```yaml
evaluation_gates:
  groundedness:           >= 0.80    # finding grounded in slide content
  relevance:              >= 0.75    # finding relevant to prompt
  schema_compliance:      >= 0.95    # output matches declared schema
  hallucination_rate:     <= 0.05    # max 5% of findings are hallucinated
  critical_regression:    = 0         # zero new critical false negatives vs current active
  overall_regression:     <= 0.02     # max 2% regression on existing test cases
```

These thresholds are configurable per agent and per Review Profile.
They do not live in code — they live in configuration.

## Gate Evaluation Flow

```
New Prompt Version (draft)
         │
         ▼
Golden Dataset
(known PPT + expected findings pairs)
         │
         ▼
TruLens Evaluation
(groundedness, relevance, schema_compliance, ...)
         │
         ▼
Regression Check
(compare findings vs current active version on same dataset)
         │
         ▼
Gate Assessment
  ├── ALL gates PASS → "Eligible for activation"
  └── ANY gate FAILS → "Draft — not eligible" (with specific gate failures listed)
         │
         ▼
Authorized user manually activates (if eligible)
```

## Gate Failure Handling

A gate failure:
- Does NOT block the current active version from running
- DOES prevent the draft from being activated
- DOES display specific failures in the Admin UI

```
Version 6 evaluation result:
  groundedness: 0.77 ✗ (threshold: 0.80)
  relevance: 0.82 ✓
  schema_compliance: 0.99 ✓
  critical_regression: 0 ✓
  overall_regression: 0.01 ✓

Status: NOT ELIGIBLE — groundedness below threshold
```

## Per-Agent Gate Configuration

Gates can be configured per agent:

```yaml
agent_gates:
  proposal_context:
    groundedness: >= 0.85      # higher threshold for proposal agent
    requirement_coverage: >= 0.90
  content:
    groundedness: >= 0.78
  cio_lens:
    groundedness: >= 0.82
```

## Model Configuration Gates

Same gate framework applies when changing the model or provider configuration:

```
Old config: gateway + gpt-4o-mini
New config: gateway + gpt-4o

→ Run evaluation on golden dataset with both configs
→ Compare metrics
→ If new config passes all gates and is better → eligible for activation
→ If not → remain on current config
```

## Related Documents

- See: [evaluation.md](evaluation.md) for TruLens framework
- See: [golden-dataset.md](golden-dataset.md) for evaluation inputs
- See: [regression-testing.md](regression-testing.md) for regression test details
- See: [../prompts/prompt-evaluation.md](../prompts/prompt-evaluation.md) for prompt evaluation flow

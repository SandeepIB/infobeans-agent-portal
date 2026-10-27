# Evaluation Documents Index

| Document | Topic |
|----------|-------|
| [evaluation.md](evaluation.md) | TruLens + LangSmith evaluation framework |
| [golden-dataset.md](golden-dataset.md) | Golden dataset structure and management |
| [evaluation-gates.md](evaluation-gates.md) | Gate thresholds; when a prompt can activate |
| [regression-testing.md](regression-testing.md) | Regression test tiers and strategy |
| [human-feedback.md](human-feedback.md) | Human feedback loop and dataset |

## Key Principle

Evaluation is NOT in the critical review path. It runs asynchronously after reviews.
If evaluation tools are unavailable, the review pipeline is unaffected.

## Evaluation Status by Capability

| Capability | Status |
|-----------|--------|
| TruLens basic metrics | NOW |
| LangSmith tracing | NOW |
| Golden dataset | NOW |
| Evaluation gates | NOW |
| Human feedback dataset | NEXT |
| Advanced regression platform | NEXT |

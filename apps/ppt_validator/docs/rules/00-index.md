# Rule Library Documents Index

| Document | Topic |
|----------|-------|
| [rule-library.md](rule-library.md) | Rule Library structure, format, and service API |
| [rule-versioning.md](rule-versioning.md) | Versioning, immutability, and activation |
| [rule-testing.md](rule-testing.md) | Testing rule-based agents |

## Core Rule

Every threshold, constraint, and rule applied by any agent lives in the Rule Library.
No rule strings or thresholds in agent Python code. Ever.

## Rule Library vs. Prompt Library

| | Rule Library | Prompt Library |
|-|-------------|----------------|
| Used by | Rule-type + hybrid agents | LLM-type agents |
| Format | Versioned YAML/JSON per domain | Versioned YAML per agent |
| Storage | DB tables `rules` / `rule_versions` | DB tables `prompt_versions` |
| Confidence | Always 1.0 (deterministic) | 0–1 (probabilistic) |

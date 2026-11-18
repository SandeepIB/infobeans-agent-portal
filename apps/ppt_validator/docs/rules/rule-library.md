# Rule Library — NOW

## Purpose

The Rule Library is the single source of truth for all rules applied by rule-based and hybrid agents.
No rule strings, thresholds, or constraints in agent Python code.

## Directory Layout (Seed Files)

```
rule_library/
  branding/
    v1.yaml
    v2.yaml
  template/
    v1.yaml
  security/
    v1.yaml
  accessibility/
    v1.yaml
  typography/
    v1.yaml
```

Seed files are loaded into the DB on first startup. Subsequent changes through Admin UI or API.

## Rule Schema (YAML)

```yaml
domain: branding
version: 2
status: active
description: "InfoBeans branding rules v2 — updated color palette"
created_by: "brand-team"

rules:
  - rule_id: "BRAND-001"
    name: "Primary background color"
    description: "Slide background must use approved primary colors"
    severity: HIGH
    auto_fixable: true
    applies_to: ["customer", "sales"]
    check:
      type: color_match
      allowed_values: ["#FFFFFF", "#002D74", "#E8F0FE"]
      element: background_fill

  - rule_id: "BRAND-002"
    name: "Logo presence"
    description: "InfoBeans logo must appear on every slide"
    severity: HIGH
    auto_fixable: false
    applies_to: ["customer", "sales", "internal"]
    check:
      type: element_presence
      element: logo
      required: true

  - rule_id: "TYPO-001"
    name: "Minimum body font size"
    severity: MEDIUM
    auto_fixable: true
    check:
      type: font_size_minimum
      element: body_text
      minimum_pt: 16
      applies_to_levels: [2, 3, 4]
```

## DB Tables

```sql
CREATE TABLE IF NOT EXISTS rule_versions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    domain        TEXT NOT NULL,
    version       INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft',
    rules_json    TEXT NOT NULL,        -- JSON string of the full rules array
    description   TEXT,
    created_by    TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(domain, version)
);

CREATE TABLE IF NOT EXISTS rule_activations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    domain           TEXT NOT NULL,
    rule_version_id  INTEGER NOT NULL REFERENCES rule_versions(id),
    business_unit    TEXT,              -- NULL = global default
    activated_by     TEXT,
    activated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## RuleService API

```python
class RuleService:
    def get_active(self, domain: str, business_unit: str | None = None) -> RuleSet:
        """Return active rule set for domain, with optional business-unit override."""

    def check(self, rule_set: RuleSet, context: dict) -> list[RuleResult]:
        """Run all rules in the set against the given context. Returns violations."""

    def create_version(self, domain: str, rules: list[dict], created_by: str) -> RuleSet:
        """Create new draft rule version."""

    def activate(self, rule_version_id: int, business_unit: str | None, activated_by: str) -> None:
        """Activate rule version globally or per business unit."""
```

## Applies-To Scope

Each rule can target specific presentation types:

| `applies_to` value | Description |
|---------------------|-------------|
| `customer` | Customer-facing presentations |
| `sales` | Internal sales materials |
| `internal` | Internal-only presentations |
| `all` | All presentation types |

## Related Documents

- See: [rule-versioning.md](rule-versioning.md) for versioning details
- See: [rule-testing.md](rule-testing.md) for testing rule-based agents

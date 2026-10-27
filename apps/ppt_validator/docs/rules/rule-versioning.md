# Rule Versioning — NOW

## Purpose

Rule versions are immutable once active. Changes create new versions. Every finding is traceable
to the exact rule version that produced it.

## Versioning Rules

1. Version numbers are integers, monotonically increasing per domain.
2. A rule version is immutable once `status` moves from `draft` to `active`.
3. To change a rule: create a new version (draft), activate it. Old version → `deprecated`.
4. Never delete a rule version — audit trail must remain intact.
5. Every `agent_run` records `rule_version_id` for rule-based agents.

## Lifecycle

```
draft → active → deprecated
```

Same as prompt versioning. See: [../prompts/prompt-lifecycle.md](../prompts/prompt-lifecycle.md)

## Business-Unit Scoping

Different business units can have different active rule versions:

```
Global default:    branding v3
Customer team:     branding v3 (inherits global)
Internal team:     branding v2 (older, less strict)
```

`RuleService.get_active(domain, business_unit)` resolves the correct version.

## Rule Activation Audit

Every activation creates an `audit_logs` entry:

```json
{
  "event_type": "rule_version_activated",
  "entity_type": "rule_version",
  "entity_id": "branding/v3",
  "actor": "brand-admin@infobeans.com",
  "payload": { "business_unit": null, "previous_version": 2 }
}
```

## Related Documents

- See: [rule-library.md](rule-library.md) for rule schema and DB tables
- See: [../architecture/10-versioning-audit.md](../architecture/10-versioning-audit.md) for audit trail

# Critic Agent

## Purpose

Reconcile findings from all agents. Identify conflicts, elevate severity where warranted, dismiss
low-quality or duplicate findings. The Critic improves signal quality — it does not add new findings.

## Inputs

- `findings` — filtered, conflicting, or uncertain findings from all agents (not all findings)
- `review_profile` — for context

## Outputs

Standard Agent Contract with reconciled findings. Score reflects overall finding quality.

## Context Scope

Critic receives only findings that need reconciliation:
- Findings that conflict between agents
- Findings with `confidence < 0.70`
- Findings where `severity = CRITICAL` and confidence is uncertain

It does NOT receive all findings — that would be too many tokens.

```yaml
context_scope:
  slides: none
  content: none
  design: none
  findings: filtered   # only conflicting/uncertain findings
```

## What Critic Does

1. For each conflicting finding pair: determine which is more accurate.
2. For each uncertain critical finding: confirm or dismiss.
3. Adjust severity if evidence supports escalation or de-escalation.
4. Produce final reconciled finding list.

## Rules

- Critic may not add new findings. It can only reconcile existing ones.
- Critic may not suppress a finding without logging its reason.
- Critic always reruns if any other agent reran (findings may have changed).

## DAG Position

Last agent before Aggregator. Runs after CIO Lens.

## Registry Entry

```yaml
agent_id: critic
type: llm
version: 1
execution_mode: sequential
dependency_stage: cross_slide
requires: [filtered_findings]
severity_default: MEDIUM
enabled_by_default: true
cacheability: none   # always reruns if anything changed
```

## Testing

- Test: two agents agree → one canonical finding returned
- Test: two agents conflict → higher-confidence finding wins
- Test: critical finding, low confidence → escalated to HUMAN_APPROVAL

## Related Documents

- See: [../architecture/finding-management.md](../architecture/finding-management.md) for deduplication
- See: [../architecture/02-agent-dag.md](../architecture/02-agent-dag.md) for DAG position

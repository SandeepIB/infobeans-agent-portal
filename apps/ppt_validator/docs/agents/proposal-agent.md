# Proposal Context Agent

## Purpose

Evaluates whether the presentation satisfies proposal requirements, client objectives, scope,
and win themes. Only runs when Proposal Context is provided.

## Inputs

- `ppt_content` — normalized slide content (text, titles, structure)
- `proposal_context` — structured proposal context (see schema below)
- `review_profile` — for audience and objective context

## Outputs

Standard Agent Contract + Proposal Coverage Matrix.

## Proposal Context Schema

```yaml
proposal_context:
  client: "ABC Bank"
  opportunity:
    name: "Digital Banking Modernization"
    objective: "Modernize digital banking platform"
  audience:
    primary: "CIO"
    secondary: ["CTO", "Business Leadership"]
  business_problem:
    - "Legacy platform has scalability limitations"
  requirements:
    - id: REQ-001
      requirement: "Cloud migration strategy"
      mandatory: true
    - id: REQ-003
      requirement: "Security architecture"
      mandatory: true
  deliverables:
    - "Target architecture"
    - "Migration roadmap"
  win_themes:
    - "Accelerated modernization"
    - "Low-risk migration"
  differentiators:
    - "Accelerator-based migration"
  evaluation_criteria:
    - "Technical capability"
    - "Security"
  constraints:
    - "Migration must happen incrementally"
```

## Eight Review Dimensions

| Dimension | What it checks |
|-----------|---------------|
| A. Requirement Coverage | Every mandatory requirement addressed? |
| B. Requirement-to-Slide Traceability | Evidence chain per requirement |
| C. Win Theme Coverage | Win themes demonstrated with evidence? |
| D. Client Pain → Solution → Value chain | Full value proposition present? |
| E. Scope and Deliverable Alignment | Missing or out-of-scope content? |
| F. Contradictions | Conflicts between proposal and slides? |
| G. Differentiation | Differentiators visible, explained, evidenced? |
| H. Proposal Completeness | Summary scorecard |

## Coverage Values

`COVERED | PARTIALLY_COVERED | MISSING | CONTRADICTED | NOT_APPLICABLE`

## Action Type Rules

| Finding | action_type |
|---------|------------|
| Missing formatting/structural label | AUTO_FIX |
| Missing requirement, contradiction, scope error | HUMAN_APPROVAL |
| Weak differentiation, weak evidence | RECOMMENDATION_ONLY |

Never `AUTO_FIX` business commitments, scope changes, pricing, or contractual matters.

## DAG Position

Runs in parallel with Content, Story, Customer agents after content extraction.
Does not depend on CIO Lens.

## Prompt

Location: `prompts/proposal_context/v1.yaml`

The prompt must instruct the model to:
- Evaluate against requirements, not generic presentation quality
- Never invent evidence not present in the PPT
- Never assume implied capability satisfies a mandatory requirement
- Return only the structured Agent Contract

## Registry Entry

```yaml
agent_id: proposal_context
type: llm
version: 1
execution_mode: parallel
dependency_stage: content_extraction
requires: [ppt_content, proposal_context]
severity_default: MEDIUM
enabled_by_default: false
context_scope:
  slides: relevant
  content: full
  design: none
  proposal_context: full
```

## Caching

`cacheability: full` — if the PPT content and proposal context are unchanged, result can be reused.

## Testing

- `MockProvider`-backed unit tests for all eight review dimensions
- Test: requirement covered → no finding
- Test: requirement missing → HIGH finding with `HUMAN_APPROVAL`
- Test: contradiction → CRITICAL finding
- Test: no proposal context provided → agent skipped (`status: skipped`)

## Failure Behaviour

- No proposal context → `status: skipped`; no findings; no score contribution
- LLM call fails after retries → `status: failed`; zero contribution to score

## Related Documents

- See: [../architecture/04-agent-contract.md](../architecture/04-agent-contract.md) for contract schema
- See: [../prompts/prompt-lifecycle.md](../prompts/prompt-lifecycle.md) for prompt management
- See: [../architecture/02-agent-dag.md](../architecture/02-agent-dag.md) for DAG position

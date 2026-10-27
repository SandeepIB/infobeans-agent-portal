# Context Optimization — NOW

## Purpose

Minimize tokens sent to LLMs without reducing review quality. This is mandatory — not optional.

## Principle

Never send the complete PPT to every agent. Each agent receives only the context it needs.

## Context Scope Definitions

Each agent declares its required context scope in the Agent Registry:

```yaml
context_scope:
  slides: all | relevant | none
  content: full | summary | title_only | none
  design: full | metadata | none
  findings: all | filtered | none
  proposal_context: full | requirements_only | none
```

## Compression Techniques (in order of preference)

### 1. Structured Metadata Extraction

Extract design properties as structured fields before sending to LLM.
Never send raw PPT binary or XML to an LLM.

```python
# Good: structured extraction
slide_metadata = {
    "layout_name": "Title and Content",
    "background_color": "#FFFFFF",
    "font_families": ["Calibri", "Arial"],
    "placeholder_count": 3,
}
# Bad: raw slide XML
slide_xml = pptx_slide._element.xml  # never send this
```

### 2. Normalized Slide Representation

Strip formatting noise. Send semantic content only.

```json
{
  "slide": 5,
  "title": "Our Migration Approach",
  "bullets": ["Phased migration", "Zero-downtime cutover", "Rollback tested"],
  "has_image": true,
  "speaker_notes": "Emphasise the parallel-run period."
}
```

### 3. Summaries for Cross-Slide Agents

CIO Lens and Critic receive:
- Content Agent summaries per slide (not raw content)
- Filtered, deduplicated findings (not all findings)

### 4. Relevant-Slide Selection

Proposal Agent receives only slides that contain text matching proposal requirements.
Use keyword/semantic pre-filter to select relevant slides before calling LLM.

### 5. Finding Selection for Critic

Critic receives only findings that:
- Conflict with another agent's finding
- Have confidence < configured threshold
- Have severity ≥ HIGH

### 6. Deterministic Preprocessing

Use deterministic preprocessing wherever possible:
- Rule-based content extraction (python-pptx)
- Regex for brand color codes
- Structural matching for layout names
- Keyword matching for requirement coverage pre-filter

Do not use an LLM to summarize something that can be summarized deterministically.

## Token Budget Check

Before each agent call, `CostGovernanceService` checks the remaining token budget.
If the budget is insufficient, the agent is skipped with `status: budget_exceeded`.

See: [../operations/cost-governance.md](../operations/cost-governance.md)

## Implementation Checklist

- [ ] `ExtractionService` produces structured slide representations (not raw content)
- [ ] Each agent's context scope declared in Agent Registry
- [ ] `ContextBuilder` service assembles the correct context slice per agent
- [ ] `ContextBuilder` applies relevant-slide selection for Proposal Agent
- [ ] CIO Lens receives summaries, not raw content
- [ ] Critic receives filtered findings, not all findings
- [ ] Context size logged in `agent_runs.input_tokens`

## Related Documents

- See: [07-context-flow.md](07-context-flow.md) for context flow diagram
- See: [../operations/caching.md](../operations/caching.md) for caching context
- See: [../operations/cost-governance.md](../operations/cost-governance.md) for token budgets

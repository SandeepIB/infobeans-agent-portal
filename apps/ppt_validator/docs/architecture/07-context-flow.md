# Context Flow

## Purpose

Define exactly what context each agent receives. Never send the full PPT to every agent.
Context minimization reduces token cost and improves LLM focus.

## Context Scopes

| Agent | Context it receives | What is excluded |
|-------|-------------------|-----------------|
| Template Agent | Layout metadata, placeholder types, layout names | Slide text content |
| Branding Agent | Color values, font families, logo positions, background fills | Slide text content |
| Security Agent | Metadata, hidden content flags, speaker notes | Slide text content |
| Accessibility Agent | Color contrast data, font sizes, alt text, layout | Full text content |
| Content Agent | Slide text, bullet points, titles | Design metadata |
| Story Agent | Slide titles + one-sentence summaries, slide sequence | Design metadata |
| Customer Agent | Slide text + audience context from profile | Design metadata |
| Proposal Agent | Proposal context + relevant slide content | Design metadata |
| CIO Lens | Compressed deck summary + key findings from other agents | Raw slide content |
| Critic Agent | Only findings requiring reconciliation | Raw slide content |
| Fix Agent | Specific finding + minimal slide context for fix | Other findings |

## Context Compression Techniques

Use these in order of preference (cheapest first):

1. **Structured metadata** — extract layout/design as structured fields, not raw PPT bytes
2. **Normalized slide representation** — title, bullets, metadata; strip formatting noise
3. **Summaries** — Content Agent summaries feed CIO Lens (not raw content)
4. **Relevant-slide selection** — Proposal Agent receives only slides relevant to each requirement
5. **Finding selection** — Critic receives only findings that conflict or need reconciliation
6. **Duplicate removal** — deduplicate before sending to Critic/CIO Lens
7. **Context truncation** — truncate to configured token limit with a sentinel marker

## Rule

Do not use an LLM to summarize something that can be summarized deterministically.
Use deterministic preprocessing wherever possible (structured extraction, regex, python-pptx).

## Context in the Review Pipeline

```
PPTX Upload
    │
Extraction Service
    ├── Layout metadata      → Template, Branding, Accessibility agents
    ├── Design metadata      → Branding, Security agents
    ├── Normalized slides    → Content, Story, Customer, Proposal agents
    └── Full slide content   → (only if explicitly required)

Content Agent output
    └── Deck summary         → CIO Lens (compressed)

All agent findings
    └── Filtered findings    → Critic (only conflicts/discrepancies)
```

## Related Documents

- See: [context-optimization.md](context-optimization.md) for optimization architecture
- See: [../operations/cost-governance.md](../operations/cost-governance.md) for token budgets
- See: [../operations/caching.md](../operations/caching.md) for caching extracted context

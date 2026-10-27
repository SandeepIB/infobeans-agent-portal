# Standard Agent Contract

## Purpose

Every agent — rule-based or LLM-based — returns exactly this shape. No agent returns free text.

## Contract Schema (JSON)

```json
{
  "agent_id": "customer_focus",
  "status": "completed",
  "score": 78,
  "findings": [
    {
      "slide": 8,
      "severity": "HIGH",
      "category": "customer_relevance",
      "title": "Too technical for executive audience",
      "description": "The slide focuses heavily on implementation details.",
      "recommendation": "Emphasize customer outcomes instead of internals.",
      "confidence": 0.91,
      "action_type": "RECOMMENDATION_ONLY",
      "rule_id": null,
      "prompt_version_id": 5
    }
  ],
  "summary": "Deck is generally customer-focused but two slides need executive framing."
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | yes | Must match registry `agent_id` |
| `status` | enum | yes | `completed \| failed \| skipped` |
| `score` | integer 0–100 | yes | Agent-level quality score |
| `findings` | array | yes | May be empty |
| `summary` | string | yes | One-paragraph summary |

### Finding Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide` | integer | yes | Slide number (1-indexed); 0 for deck-level |
| `severity` | enum | yes | `LOW \| MEDIUM \| HIGH \| CRITICAL` |
| `category` | string | yes | Domain category (agent-specific) |
| `title` | string | yes | Short finding title |
| `description` | string | yes | What was found |
| `recommendation` | string | yes | What to do about it |
| `confidence` | float 0–1 | yes | Agent's confidence in the finding |
| `action_type` | enum | yes | `AUTO_FIX \| HUMAN_APPROVAL \| RECOMMENDATION_ONLY` |
| `rule_id` | string\|null | yes | Rule that triggered this (null for LLM findings) |
| `prompt_version_id` | integer\|null | yes | Prompt version that produced this (null for rule findings) |

## Action Type Rules

| action_type | When to use | May Fix Agent apply? |
|-------------|-------------|---------------------|
| `AUTO_FIX` | Mechanical, deterministic correction (font size, color code) | Yes |
| `HUMAN_APPROVAL` | Business, legal, scope, pricing, contractual, contradictions | Never |
| `RECOMMENDATION_ONLY` | Suggestions; subjective improvements | Never |

Never default an ambiguous finding to `AUTO_FIX`.
Never `AUTO_FIX` business commitments, scope, pricing, or contractual matters.

## Python Implementation

Canonical dataclass lives in `agents/base.py`. Wire format is JSON. When writing an LLM-based
agent, validate the parsed response against this schema before constructing the dataclass.

## Related Documents

- See: [02-agent-dag.md](02-agent-dag.md) for when agents run
- See: [../agents/agent-contract.md](../agents/agent-contract.md) for agent development guide
- See: [scoring.md](scoring.md) for how scores are aggregated
- See: [finding-management.md](finding-management.md) for deduplication

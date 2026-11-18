# Model Routing — NEXT

## Status: NEXT

Architecture required now. Implementation follows after Phase 1 agents are stable.

## Purpose

Route each agent's LLM call to the appropriate model based on task requirements, not hard-coding.
Model names must NOT appear in agent code.

## ModelRoutingService

```python
class ModelRoutingService:
    def resolve(
        self,
        agent_id: str,
        task_complexity: str,        # "mechanical" | "simple" | "moderate" | "complex"
        review_profile: str,
        token_budget_remaining: int,
        latency_requirement: str,    # "fast" | "standard" | "quality"
    ) -> ModelConfig:
        """Return model + provider to use for this agent call."""
```

## Routing Strategy

| Task type | Model tier | Examples |
|----------|-----------|---------|
| No LLM needed | — | Mechanical rule checks |
| Simple classification | Cheap/fast | Brand color check with LLM assist |
| Content review | Economical | Content Agent, Story Agent |
| Deep analysis | Stronger | Customer Agent, Proposal Agent |
| Executive lens | Strong | CIO Lens |
| Adversarial critic | Strong | Critic Agent |
| Evaluation | Inexpensive evaluator | TruLens evaluation jobs |

## Routing Configuration (YAML, not code)

```yaml
model_routing:
  default_provider: gateway
  default_model: gpt-4o-mini

  agent_overrides:
    cio_lens:
      model: gpt-4o
      provider: gateway
    proposal_context:
      model: gpt-4o
      provider: gateway
    critic:
      model: gpt-4o
      provider: gateway
    content:
      model: gpt-4o-mini
      provider: gateway
    story:
      model: gpt-4o-mini
      provider: gateway

  budget_fallback:
    # When token budget is low, downgrade to cheaper model
    threshold_remaining_tokens: 10000
    fallback_model: gpt-4o-mini

  provider_fallback:
    # When primary provider is down, try secondary
    gateway:
      fallback: litellm
```

## Rules

- Model configuration lives in routing config, not in agent code.
- Agents call `ModelRoutingService.resolve(...)` to get `ModelConfig`.
- `ModelConfig` is passed to `LLMProvider.complete()` via kwargs.
- Budget-aware routing: downgrade model if token budget is nearly exhausted.
- Provider-aware routing: fall back to secondary provider on circuit-breaker trip.

## Phase 1 Simplification

Until `ModelRoutingService` is implemented, use a single model from `.env`.
`GATEWAY_MODEL` applies to all agents. Routing config is a no-op pass-through.

## Related Documents

- See: [06-llm-provider.md](06-llm-provider.md) for provider architecture
- See: [../operations/cost-governance.md](../operations/cost-governance.md) for budget integration
- See: [execution-controls.md](execution-controls.md) for concurrency

# Coding Guidelines — NOW

## Python

- Python 3.11+
- Type hints on all public functions and class methods
- Dataclasses for data structures (not dicts)
- Abstract base classes for interfaces (`ABC`, `@abstractmethod`)
- Dependency injection — pass dependencies through constructors, not global singletons
- No inline prompt strings — use `PromptService`
- No inline rule thresholds — use `RuleService`
- No direct LLM calls — use `LLMProvider`

## Error Handling

- Agents catch all exceptions and return `status: failed` — never propagate
- Services raise typed exceptions (`PromptNotFoundError`, `LLMStructuredOutputError`, etc.)
- Do not use bare `except Exception` in service layer — catch and re-raise with context

## Comments

Write no comments. Only add one when the WHY is non-obvious: a hidden constraint, a subtle
invariant, a workaround for a known issue. Do not explain WHAT the code does.

## Naming

- `agent_id` snake_case everywhere (registry, DB, contract)
- `review_run_id` — UUID string
- `prompt_version_id` — integer FK
- Service classes: `XService` suffix
- Agent classes: `XAgent` suffix
- Provider classes: `XProvider` suffix

## TypeScript (Frontend)

- TypeScript strict mode
- React functional components with hooks
- No inline API calls in components — use `api/` client modules
- Types for all API response shapes
- No `any` type

## File Structure — New Code Only

```
agents/          one file per agent
llm/providers/   one file per provider
services/        one file per service
api/             one file per router
tests/unit/      mirrors source structure
tests/integration/
```

Do not add files to frozen directories (`validator/`, `static/`).

## Related Documents

- See: [testing.md](testing.md) for test conventions
- See: [adding-agent.md](adding-agent.md) for agent implementation pattern

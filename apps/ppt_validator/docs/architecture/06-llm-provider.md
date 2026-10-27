# LLM Provider Architecture

## Design Principle

No agent, service, or utility knows which LLM it is talking to. All model access goes through the
`LLMProvider` ABC. The concrete provider is resolved once at startup. Swapping providers is a
one-line `.env` change — zero code changes.

## Provider Interface (`llm/provider.py`)

```python
class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, schema: dict | None = None, **kwargs) -> dict:
        """Send prompt, return parsed structured response. Never return raw text."""

    @abstractmethod
    def health(self) -> bool:
        """Return True if the provider is reachable."""
```

`ProviderFactory.from_env()` reads `LLM_PROVIDER` and returns the correct concrete instance.
Agents call `ProviderFactory.from_env()` once or receive it via dependency injection.
Agents never instantiate a provider directly.

## Supported Providers

| `LLM_PROVIDER` value | Class | Backing service |
|---------------------|-------|----------------|
| `gateway` (default) | `GatewayProvider` | InfoBeans gateway (`gateway.creatingwow.in`) |
| `litellm` | `LiteLLMProvider` | LiteLLM proxy — routes to any model |
| `claude` | `ClaudeProvider` | Anthropic Claude API (direct) |
| `groq` | `GroqProvider` | Groq API (direct) |
| `gemini` | `GeminiProvider` | Google Gemini API (direct) |
| `openai` | `OpenAIProvider` | OpenAI API (direct) |
| `mock` | `MockProvider` | Deterministic test doubles — no network calls |

## .env Reference

```dotenv
# Provider selection (one of: gateway | litellm | claude | groq | gemini | openai | mock)
LLM_PROVIDER=gateway

# InfoBeans Gateway
GATEWAY_URL=https://gateway.creatingwow.in
GATEWAY_API_KEY=<placeholder>
GATEWAY_MODEL=gpt-4o
GATEWAY_TIMEOUT_SECONDS=60

# LiteLLM proxy
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=<placeholder>
LITELLM_MODEL=claude-3-5-sonnet-20241022

# Anthropic Claude direct
ANTHROPIC_API_KEY=<placeholder>
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096

# Groq direct
GROQ_API_KEY=<placeholder>
GROQ_MODEL=llama-3.3-70b-versatile

# Google Gemini direct
GEMINI_API_KEY=<placeholder>
GEMINI_MODEL=gemini-1.5-pro

# OpenAI direct
OPENAI_API_KEY=<placeholder>
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1

# Shared settings
LLM_TEMPERATURE=0.2
LLM_MAX_RETRIES=3
LLM_RETRY_BACKOFF_SECONDS=2
```

Never commit real keys. Use `.env.example` with `<placeholder>` values.

## Structured Output Contract

Every provider must honour the `schema` parameter:
- Use native structured output if available (OpenAI `response_format`, Anthropic tool-use, etc.)
- If not: append the JSON schema to the prompt and parse + validate before returning.
- On parse failure after `LLM_MAX_RETRIES` attempts: raise `LLMStructuredOutputError`.
- Never return raw text or a partially parsed dict.

## Audit Logging

Every provider call writes one row to `llm_request`:

```sql
provider          TEXT   -- e.g. "groq"
model             TEXT   -- exact model string used
prompt_hash       TEXT   -- SHA-256 of the rendered prompt
input_tokens      INT
output_tokens     INT
cached_tokens     INT
latency_ms        INT
status            TEXT   -- "success" | "error"
error_message     TEXT
agent_run_id      FK
prompt_version_id FK
cost_usd          REAL
```

## Langsmith Integration

Langsmith tracing is added at the `LLMProvider` base class level — one wrapper, all providers traced.

```python
from langsmith import traceable

class LLMProvider(ABC):
    @traceable(name="llm_complete", run_type="llm")
    def complete(self, ...):
        return self._complete(...)
```

Set `LANGSMITH_ENABLED=false` to disable with zero code changes.

## Testing Rule

`MockProvider` returns deterministic fixtures keyed on `prompt_hash`. Tests must never set
`LLM_PROVIDER` to anything other than `mock`. A test importing a real provider class directly is a bug.

## Adding a New Provider

1. Create `llm/providers/my_provider.py` implementing `LLMProvider`.
2. Add `"myprovider": MyProvider` to `_REGISTRY` in `ProviderFactory`.
3. Add env vars to `.env.example` with comments.
4. Write a `MockProvider`-backed unit test.
5. Document the new value in the table above.

See: [../development/adding-provider.md](../development/adding-provider.md)

## Related Documents

- See: [model-routing.md](model-routing.md) for routing by agent/complexity/budget
- See: [../operations/cost-governance.md](../operations/cost-governance.md) for token budgets
- See: [../operations/caching.md](../operations/caching.md) for response caching
- See: [../operations/observability.md](../operations/observability.md) for tracing

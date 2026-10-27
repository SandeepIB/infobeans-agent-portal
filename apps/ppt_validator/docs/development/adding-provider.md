# Adding a New LLM Provider — Step-by-Step Guide

## Overview

Adding a provider requires: implementing `LLMProvider`, registering it, adding env vars,
and writing a unit test. No other changes needed.

## Steps

### 1. Create the Provider

Create `llm/providers/my_provider.py`:

```python
from llm.provider import LLMProvider

class MyProvider(LLMProvider):
    def __init__(self):
        self.base_url = os.getenv("MYPROVIDER_URL")
        self.api_key = os.getenv("MYPROVIDER_API_KEY")
        self.model = os.getenv("MYPROVIDER_MODEL")

    def complete(self, prompt: str, schema: dict | None = None, **kwargs) -> dict:
        # Call the provider API
        # If schema provided: enforce structured output
        # If not: append schema to prompt and parse response
        # On parse failure after LLM_MAX_RETRIES: raise LLMStructuredOutputError
        # Never return raw text — always return a dict
        ...

    def health(self) -> bool:
        # Return True if provider is reachable
        ...
```

### 2. Register the Provider

In `llm/provider.py`, add to `_REGISTRY`:

```python
_REGISTRY = {
    "gateway": GatewayProvider,
    "litellm": LiteLLMProvider,
    "claude": ClaudeProvider,
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "mock": MockProvider,
    "myprovider": MyProvider,   # add this line
}
```

### 3. Add Env Vars to `.env.example`

```dotenv
# ── My Provider ───────────────────────────────────────────────────────────────
MYPROVIDER_URL=https://api.myprovider.com
MYPROVIDER_API_KEY=<placeholder>
MYPROVIDER_MODEL=my-model-v1
```

Never commit real keys. Placeholders only in `.env.example`.

### 4. Document the Provider

Update [../architecture/06-llm-provider.md](../architecture/06-llm-provider.md) — add a row to the
Supported Providers table.

### 5. Write a Unit Test

```python
def test_my_provider_returns_structured_output():
    provider = MyProvider()
    # Use MockProvider pattern: mock the HTTP call
    with patch("llm.providers.my_provider.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"content": '{"score": 80, ...}'}
        result = provider.complete(prompt="...", schema=AGENT_CONTRACT_SCHEMA)
    assert isinstance(result, dict)
    assert "score" in result

def test_my_provider_health():
    provider = MyProvider()
    with patch("...") as mock:
        mock.return_value.ok = True
        assert provider.health() is True
```

Tests must not call the real provider API.

## Structured Output Requirement

Every provider must honour the `schema` parameter:
- Use native structured output if the API supports it
- Otherwise: append schema to prompt + parse + validate
- On failure after `LLM_MAX_RETRIES`: raise `LLMStructuredOutputError`
- Never return raw text

## Related Documents

- See: [../architecture/06-llm-provider.md](../architecture/06-llm-provider.md) for provider architecture
- See: [testing.md](testing.md) for test patterns

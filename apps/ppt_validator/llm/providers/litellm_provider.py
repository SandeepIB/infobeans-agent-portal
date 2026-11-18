import json
import os
import litellm
from llm.provider import LLMProvider, LLMResponse, LLMStructuredOutputError, ProviderFactory, parse_llm_json


class LiteLLMProvider(LLMProvider):

    def __init__(self) -> None:
        self._model = os.getenv("LITELLM_MODEL", "gpt-4o")
        self._api_key = os.getenv("LITELLM_API_KEY", "")
        self._base_url = os.getenv("LITELLM_BASE_URL", "")
        self._temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        user_msg = user
        if schema:
            user_msg += f"\n\nRespond with valid JSON matching:\n{json.dumps(schema)}"

        resp = litellm.completion(
            model=kwargs.get("model", self._model),
            api_key=self._api_key or None,
            api_base=self._base_url or None,
            temperature=kwargs.get("temperature", self._temperature),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
        )
        raw = resp.choices[0].message.content
        try:
            content = parse_llm_json(raw)
        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(f"LiteLLM response not valid JSON: {exc}") from exc

        return LLMResponse(
            content=content,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            cached_tokens=0,
            latency_ms=0,
            model=self._model,
            provider="litellm",
        )

    def health(self) -> bool:
        return True


ProviderFactory.register("litellm", LiteLLMProvider)

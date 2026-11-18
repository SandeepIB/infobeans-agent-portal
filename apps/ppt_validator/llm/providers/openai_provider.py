import json
import os
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from llm.provider import LLMProvider, LLMResponse, LLMStructuredOutputError, ProviderFactory, parse_llm_json


class OpenAIProvider(LLMProvider):

    def __init__(self) -> None:
        raw_client = openai.OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        try:
            from langsmith.wrappers import wrap_openai
            self._client = wrap_openai(raw_client)
        except Exception:
            self._client = raw_client
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self._temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2), reraise=True)
    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        kwargs_call: dict = dict(
            model=kwargs.get("model", self._model),
            temperature=kwargs.get("temperature", self._temperature),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        if schema:
            kwargs_call["response_format"] = {"type": "json_object"}
            kwargs_call["messages"][-1]["content"] += f"\n\nRespond with valid JSON matching:\n{json.dumps(schema)}"

        resp = self._client.chat.completions.create(**kwargs_call)
        raw = resp.choices[0].message.content
        try:
            content = parse_llm_json(raw)
        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(f"OpenAI response not valid JSON: {exc}") from exc

        return LLMResponse(
            content=content,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            cached_tokens=getattr(resp.usage, "cached_tokens", 0),
            latency_ms=0,
            model=self._model,
            provider="openai",
        )

    def health(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


ProviderFactory.register("openai", OpenAIProvider)

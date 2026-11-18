import json
import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from llm.provider import LLMProvider, LLMResponse, LLMStructuredOutputError, ProviderFactory, parse_llm_json


class GroqProvider(LLMProvider):

    def __init__(self) -> None:
        self._client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self._model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self._temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2), reraise=True)
    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        user_msg = user
        if schema:
            user_msg += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}"

        resp = self._client.chat.completions.create(
            model=kwargs.get("model", self._model),
            temperature=kwargs.get("temperature", self._temperature),
            response_format={"type": "json_object"} if schema else None,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
        )
        raw = resp.choices[0].message.content
        try:
            content = parse_llm_json(raw)
        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(f"Groq response not valid JSON: {exc}") from exc

        return LLMResponse(
            content=content,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            cached_tokens=0,
            latency_ms=0,
            model=self._model,
            provider="groq",
        )

    def health(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


ProviderFactory.register("groq", GroqProvider)

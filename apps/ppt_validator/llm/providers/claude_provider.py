import json
import os
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from llm.provider import LLMProvider, LLMResponse, LLMStructuredOutputError, ProviderFactory, parse_llm_json


class ClaudeProvider(LLMProvider):

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
        )
        self._model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self._max_tokens = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))
        self._temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        user_msg = user
        if schema:
            user_msg += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}"

        try:
            resp = self._client.messages.create(
                model=kwargs.get("model", self._model),
                max_tokens=kwargs.get("max_tokens", self._max_tokens),
                temperature=kwargs.get("temperature", self._temperature),
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text
            content = parse_llm_json(raw)
            return LLMResponse(
                content=content,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                cached_tokens=0,
                latency_ms=0,
                model=self._model,
                provider="claude",
            )
        except Exception as exc:
            import structlog
            structlog.get_logger().error("claude_llm_call_failed", error=str(exc), model=self._model)
            raise

    def health(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False


ProviderFactory.register("claude", ClaudeProvider)

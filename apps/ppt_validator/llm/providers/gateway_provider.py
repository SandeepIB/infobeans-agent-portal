import json
import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from llm.provider import LLMProvider, LLMResponse, LLMStructuredOutputError, ProviderFactory, parse_llm_json


class GatewayProvider(LLMProvider):

    def __init__(self) -> None:
        self._url = os.environ["GATEWAY_URL"].rstrip("/") + "/v1/chat/completions"
        self._api_key = os.environ["GATEWAY_API_KEY"]
        self._model = os.getenv("GATEWAY_MODEL", "gpt-4o")
        self._timeout = int(os.getenv("GATEWAY_TIMEOUT_SECONDS", "60"))
        self._temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        payload: dict = {
            "model": kwargs.get("model", self._model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self._temperature),
        }
        if schema:
            payload["response_format"] = {"type": "json_object"}
            payload["messages"][-1]["content"] += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}"

        resp = requests.post(
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]

        try:
            content = parse_llm_json(raw)
        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(f"Gateway response not valid JSON: {exc}") from exc

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cached_tokens=usage.get("cached_tokens", 0),
            latency_ms=0,
            model=self._model,
            provider="gateway",
        )

    def health(self) -> bool:
        try:
            r = requests.get(self._url.replace("/chat/completions", "/models"), timeout=5,
                             headers={"Authorization": f"Bearer {self._api_key}"})
            return r.status_code == 200
        except Exception:
            return False


ProviderFactory.register("gateway", GatewayProvider)

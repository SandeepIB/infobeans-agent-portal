import hashlib
import json
from llm.provider import LLMProvider, LLMResponse, ProviderFactory


class MockProvider(LLMProvider):
    """Deterministic test double. Never calls any real API."""

    _fixtures: dict[str, dict] = {}

    @classmethod
    def register_fixture(cls, system: str, user: str, response: dict) -> None:
        key = hashlib.sha256(f"{system}\n{user}".encode()).hexdigest()
        cls._fixtures[key] = response

    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        key = self.prompt_hash(system, user)
        content = self._fixtures.get(key, self._default_response())
        return LLMResponse(
            content=content,
            input_tokens=100,
            output_tokens=50,
            cached_tokens=0,
            latency_ms=1,
            model="mock",
            provider="mock",
        )

    def health(self) -> bool:
        return True

    @staticmethod
    def _default_response() -> dict:
        return {
            "agent_id": "mock",
            "status": "completed",
            "score": 80,
            "findings": [],
            "summary": "Mock response — no fixture registered for this prompt.",
        }


ProviderFactory.register("mock", MockProvider)

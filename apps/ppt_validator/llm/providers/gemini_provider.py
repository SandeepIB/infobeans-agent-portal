import json
import os
from llm.provider import LLMProvider, LLMResponse, LLMStructuredOutputError, ProviderFactory, parse_llm_json


class GeminiProvider(LLMProvider):

    def __init__(self) -> None:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self._model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        self._temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
        self._genai = genai

    def _complete(self, system: str, user: str, schema: dict | None = None, **kwargs) -> LLMResponse:
        import google.generativeai as genai
        model = self._genai.GenerativeModel(
            model_name=kwargs.get("model", self._model_name),
            system_instruction=system,
            generation_config=self._genai.GenerationConfig(temperature=kwargs.get("temperature", self._temperature)),
        )
        prompt = user
        if schema:
            prompt += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}"

        resp = model.generate_content(prompt)
        raw = resp.text
        try:
            content = parse_llm_json(raw)
        except json.JSONDecodeError as exc:
            raise LLMStructuredOutputError(f"Gemini response not valid JSON: {exc}") from exc

        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            content=content,
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            cached_tokens=0,
            latency_ms=0,
            model=self._model_name,
            provider="gemini",
        )

    def health(self) -> bool:
        try:
            self._genai.list_models()
            return True
        except Exception:
            return False


ProviderFactory.register("gemini", GeminiProvider)

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
import os
import time
import structlog

import ast
import re

logger = structlog.get_logger()


@dataclass
class LLMResponse:
    content: dict
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    latency_ms: int
    model: str
    provider: str


class LLMStructuredOutputError(Exception):
    pass


def parse_llm_json(raw: str) -> dict | list:
    """Parse JSON content from LLM response, stripping markdown codeblocks, single quotes, or extraneous text."""
    if not isinstance(raw, str):
        raise ValueError(f"Expected string raw content, got {type(raw).__name__}")

    text = raw.strip()

    # 1. Direct standard JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    def _try_parse(s: str):
        s_clean = s.strip()
        if not s_clean:
            return None
        # Try direct
        try:
            return json.loads(s_clean)
        except json.JSONDecodeError:
            pass
        # Try trailing comma fix
        try:
            no_trailing_comma = re.sub(r',\s*([}\]])', r'\1', s_clean)
            return json.loads(no_trailing_comma)
        except json.JSONDecodeError:
            pass
        # Try python literal eval (handles single quotes e.g. {'score': 80})
        try:
            ast_prep = s_clean.replace("true", "True").replace("false", "False").replace("null", "None")
            res = ast.literal_eval(ast_prep)
            if isinstance(res, (dict, list)):
                return res
        except Exception:
            pass
        return None

    # 2. Try parsing stripped markdown codeblock
    if "```" in text:
        lines = []
        in_code_block = False
        for line in text.splitlines():
            line_str = line.strip()
            if line_str.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                lines.append(line)
        if lines:
            res = _try_parse("\n".join(lines))
            if res is not None:
                return res

    # 3. Try parsing sliced substring from first { or [ to last } or ]
    start_curly = text.find("{")
    end_curly = text.rfind("}")
    start_bracket = text.find("[")
    end_bracket = text.rfind("]")

    start = -1
    end = -1

    if start_curly != -1 and end_curly != -1 and end_curly > start_curly:
        if start_bracket != -1 and start_bracket < start_curly and end_bracket > end_curly:
            start, end = start_bracket, end_bracket
        else:
            start, end = start_curly, end_curly
    elif start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
        start, end = start_bracket, end_bracket

    if start != -1 and end != -1:
        substring = text[start : end + 1]
        res = _try_parse(substring)
        if res is not None:
            return res

    # 4. Try _try_parse on full text
    res = _try_parse(text)
    if res is not None:
        return res

    # Re-raise standard JSONDecodeError by calling json.loads(raw)
    return json.loads(raw)


# ── LangSmith Environment Setup ───────────────────────────────────────────────
def _setup_langsmith_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if api_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGCHAIN_API_KEY"] = api_key
        project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT", "infobeans-infobeans-ppt-validate")
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGCHAIN_PROJECT"] = project
        endpoint = os.getenv("LANGSMITH_ENDPOINT") or os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

_setup_langsmith_env()

try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


class LLMBudgetExceededError(Exception):
    pass


class LLMProvider(ABC):

    def complete(
        self,
        system: str,
        user: str,
        schema: dict | None = None,
        **kwargs,
    ) -> LLMResponse:
        start = time.monotonic()
        result = self._complete(system, user, schema, **kwargs)
        result.latency_ms = int((time.monotonic() - start) * 1000)
        return result

    @abstractmethod
    def _complete(
        self,
        system: str,
        user: str,
        schema: dict | None = None,
        **kwargs,
    ) -> LLMResponse:
        ...

    @abstractmethod
    def health(self) -> bool:
        ...

    @staticmethod
    def prompt_hash(system: str, user: str) -> str:
        return hashlib.sha256(f"{system}\n{user}".encode()).hexdigest()


class ProviderFactory:
    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type) -> None:
        cls._registry[name] = provider_cls

    @classmethod
    def from_env(cls) -> LLMProvider:
        name = os.getenv("LLM_PROVIDER", "gateway").lower()
        if name not in cls._registry:
            raise ValueError(f"Unknown LLM_PROVIDER: {name}. Valid: {list(cls._registry)}")
        return cls._registry[name]()

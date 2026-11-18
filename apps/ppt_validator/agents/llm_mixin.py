"""LLM agent mixin — shared logic for all LLM-backed agents."""
from __future__ import annotations
import json
import os
import re
from agents.base import AgentContract, Finding, Severity, ActionType, Evidence
from llm.provider import ProviderFactory, LLMResponse
from services.prompt_service import PromptService
from services.cache_service import CacheService
from services.cost_governance_service import CostGovernanceService
import structlog

logger = structlog.get_logger()
_prompt_svc = PromptService()
_cache_svc = CacheService()
_cost_svc = CostGovernanceService()


try:
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def get_current_run_tree():
        return None


def _normalize_model_name(name: str | None) -> str:
    if not name or "mock" in name.lower():
        return "claude-3-5-sonnet-20241022"
    if "claude" in name.lower() and "202" not in name:
        return "claude-3-5-sonnet-20241022"
    return name


class LLMAgentMixin:
    """Mix into ReviewAgent subclasses that call an LLM."""

    agent_id: str

    def _llm_call(self, context: dict, system: str, user: str,
                  prompt_version_id: int | None = None) -> dict | None:
        run_id = context.get("run_id", "")
        provider = ProviderFactory.from_env()
        model = os.getenv("CLAUDE_MODEL", os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"))

        messages_payload = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if LANGSMITH_AVAILABLE:
            parent_tree = context.get("parent_run_tree") or get_current_run_tree()
            model_name = _normalize_model_name(model)
            display_node_name = f"agent_{self.agent_id} ({model_name})"

            if parent_tree:
                child = parent_tree.create_child(
                    name=display_node_name,
                    run_type="chain",
                    inputs={"messages": messages_payload},
                    extra={
                        "metadata": {
                            "ls_provider": provider.__class__.__name__.lower().replace("provider", ""),
                            "ls_model_name": model_name,
                            "agent_id": self.agent_id,
                        }
                    }
                )
                child.post()

                cached = _cache_svc.get(provider.__class__.__name__, model, prompt_version_id, system, user)
                if cached:
                    logger.info("cache_hit", agent_id=self.agent_id, run_id=run_id)
                    res_content = cached
                    in_tok, out_tok = 0, 0
                else:
                    ok, reason = _cost_svc.check_budget(run_id)
                    if not ok:
                        logger.warning("budget_exceeded", agent_id=self.agent_id, reason=reason)
                        child.end(error=reason)
                        child.patch()
                        return None

                    resp: LLMResponse = provider.complete(system=system, user=user, agent_id=self.agent_id)
                    _cost_svc.record(run_id, self.agent_id, resp.input_tokens, resp.output_tokens,
                                     resp.cached_tokens, resp.provider, resp.model)
                    if resp.content and isinstance(resp.content, (dict, list)):
                        _cache_svc.set(provider.__class__.__name__, model, prompt_version_id, system, user,
                                       resp.content, resp.input_tokens, resp.output_tokens)
                    res_content = resp.content
                    in_tok, out_tok = resp.input_tokens, resp.output_tokens
                    model_name = _normalize_model_name(resp.model or model)
                    display_node_name = f"agent_{self.agent_id} ({model_name})"
                    child.name = display_node_name

                tot_tok = in_tok + out_tok
                formatted_text = json.dumps(res_content) if isinstance(res_content, (dict, list)) else str(res_content)
                child.end(
                    outputs={
                        "generations": [
                            {
                                "text": formatted_text,
                                "message": {
                                    "role": "assistant",
                                    "content": formatted_text,
                                }
                            }
                        ],
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": formatted_text,
                            }
                        }],
                        "llm_output": {
                            "token_usage": {
                                "prompt_tokens": in_tok,
                                "completion_tokens": out_tok,
                                "total_tokens": tot_tok,
                            },
                            "model_name": model_name,
                        },
                        "usage": {
                            "prompt_tokens": in_tok,
                            "completion_tokens": out_tok,
                            "total_tokens": tot_tok,
                        },
                        "usage_metadata": {
                            "input_tokens": in_tok,
                            "output_tokens": out_tok,
                            "total_tokens": tot_tok,
                        },
                        "model": model_name,
                        "model_name": model_name,
                    }
                )
                child.patch()
                return res_content

            @traceable(name=display_node_name, run_type="chain")
            def _traced_llm_execution(messages: list[dict]):
                cached = _cache_svc.get(provider.__class__.__name__, model, prompt_version_id, system, user)
                if cached:
                    logger.info("cache_hit", agent_id=self.agent_id, run_id=run_id)
                    model_name = _normalize_model_name(model)
                    return {
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(cached) if isinstance(cached, (dict, list)) else str(cached),
                            }
                        }],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        "usage_metadata": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                        "model": model_name,
                        "model_name": model_name,
                        "cached": True,
                        "_content": cached,
                    }

                ok, reason = _cost_svc.check_budget(run_id)
                if not ok:
                    logger.warning("budget_exceeded", agent_id=self.agent_id, reason=reason)
                    return {"_content": None}

                resp: LLMResponse = provider.complete(system=system, user=user, agent_id=self.agent_id)
                _cost_svc.record(run_id, self.agent_id, resp.input_tokens, resp.output_tokens,
                                 resp.cached_tokens, resp.provider, resp.model)
                if resp.content and isinstance(resp.content, (dict, list)):
                    _cache_svc.set(provider.__class__.__name__, model, prompt_version_id, system, user,
                                   resp.content, resp.input_tokens, resp.output_tokens)

                model_name = _normalize_model_name(resp.model or model)
                total_tokens = resp.input_tokens + resp.output_tokens

                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(resp.content) if isinstance(resp.content, (dict, list)) else str(resp.content),
                        }
                    }],
                    "usage": {
                        "prompt_tokens": resp.input_tokens,
                        "completion_tokens": resp.output_tokens,
                        "total_tokens": total_tokens,
                    },
                    "usage_metadata": {
                        "input_tokens": resp.input_tokens,
                        "output_tokens": resp.output_tokens,
                        "total_tokens": total_tokens,
                    },
                    "model": model_name,
                    "model_name": model_name,
                    "provider": resp.provider,
                    "_content": resp.content,
                }

            traced_res = _traced_llm_execution(messages=messages_payload)
            return traced_res["_content"]
        else:
            cached = _cache_svc.get(provider.__class__.__name__, model, prompt_version_id, system, user)
            if cached:
                logger.info("cache_hit", agent_id=self.agent_id, run_id=run_id)
                return cached

            ok, reason = _cost_svc.check_budget(run_id)
            if not ok:
                logger.warning("budget_exceeded", agent_id=self.agent_id, reason=reason)
                return None

            resp: LLMResponse = provider.complete(system=system, user=user, agent_id=self.agent_id)
            _cost_svc.record(run_id, self.agent_id, resp.input_tokens, resp.output_tokens,
                             resp.cached_tokens, resp.provider, resp.model)
            if resp.content and isinstance(resp.content, (dict, list)):
                _cache_svc.set(provider.__class__.__name__, model, prompt_version_id, system, user,
                               resp.content, resp.input_tokens, resp.output_tokens)
            return resp.content

    def _get_prompt(self, context: dict) -> dict:
        profile = context.get("profile", {})
        overrides = profile.get("prompt_overrides", {})
        version_id = overrides.get(self.agent_id)
        return _prompt_svc.get_active(self.agent_id, version_id)

    @staticmethod
    def _format_prompt(template: str, **kwargs) -> str:
        """Substitute {word} placeholders only — leaves JSON braces in templates untouched."""
        def _sub(m: re.Match) -> str:
            key = m.group(1)
            return str(kwargs[key]) if key in kwargs else m.group(0)
        return re.sub(r'\{(\w+)\}', _sub, template)

    def _parse_findings(self, raw: dict) -> list[Finding]:
        findings = []
        raw_findings = raw.get("findings", [])
        for idx, f in enumerate(raw_findings):
            try:
                raw_sev = str(f.get("severity", "LOW")).upper()
                if raw_sev in ("CRITICAL", "HIGH"):
                    sev = Severity.HIGH
                elif raw_sev == "MEDIUM":
                    sev = Severity.MEDIUM
                elif raw_sev == "INFO":
                    sev = Severity.INFO
                else:
                    sev = Severity.LOW

                raw_act = str(f.get("action_type", "RECOMMENDATION_ONLY")).upper()
                if raw_act in ("AUTO_FIXABLE", "AUTO_FIX"):
                    act = ActionType.AUTO_FIXABLE
                elif raw_act in ("HUMAN_REVIEW_REQUIRED", "HUMAN_APPROVAL"):
                    act = ActionType.HUMAN_REVIEW_REQUIRED
                else:
                    act = ActionType.RECOMMENDATION_ONLY

                conf = float(f.get("confidence", 0.85))
                conf = max(0.0, min(1.0, conf))

                finding_id = f.get("id") or f"{self.agent_id.upper()[:3]}-{idx+1:03d}"
                desc = f.get("finding") or f.get("description") or f.get("detail", "")
                ev = f.get("evidence") or desc

                findings.append(Finding(
                    id=finding_id,
                    slide=int(f.get("slide", 0)),
                    severity=sev,
                    category=f.get("category", self.agent_id),
                    title=f.get("title", f.get("finding", "Finding")),
                    description=desc,
                    recommendation=f.get("recommendation", ""),
                    confidence=conf,
                    action_type=act,
                    rule_id=f.get("rule_id"),
                    evidence=ev,
                ))
            except Exception:
                continue
        return findings

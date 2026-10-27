# Adding a New Agent — Step-by-Step Guide

## Overview

Adding an agent requires: registry entry, implementation, prompt/rules, DAG wiring, profile config,
and tests. Do not touch any legacy file.

## Checklist

### 1. Registry Entry

Add to `agents/registry.yaml`:

```yaml
- agent_id: legal_compliance
  name: Legal Compliance Agent
  type: llm
  version: 1
  execution_mode: parallel
  dependency_stage: content_extraction
  requires: [ppt_content]
  severity_default: HIGH
  enabled_by_default: false
  context_scope:
    slides: all
    content: full
    design: none
  cacheability: slide_level
  affected_by: [content]
```

### 2. Implement the Agent

Create `agents/legal_compliance.py`:

```python
from agents.base import ReviewAgent, AgentContract
from services.prompt_service import PromptService
from llm.provider import LLMProvider

class LegalComplianceAgent(ReviewAgent):
    agent_id = "legal_compliance"

    def __init__(self, llm_provider: LLMProvider, prompt_service: PromptService):
        self.llm_provider = llm_provider
        self.prompt_service = prompt_service

    def run(self, context: dict) -> AgentContract:
        prompt_version = self.prompt_service.get_active(self.agent_id, context["review_profile"])
        rendered = self.prompt_service.render(prompt_version, self._build_variables(context))
        response = self.llm_provider.complete(
            system=rendered.system_role,
            user=rendered.user_message,
            schema=rendered.output_schema,
        )
        return self._parse_response(response, prompt_version.id)
```

### 3. Add Prompt (LLM agent)

Create `prompts/legal_compliance/v1.yaml` — see [../prompts/prompt-schema.md](../prompts/prompt-schema.md).

Include:
- System role
- User template with `{{variables}}`
- Output schema (Agent Contract)
- Few-shot examples if needed

### 4. Add Rules (rule-based agent)

Create `rule_library/legal/v1.yaml` — see [../rules/rule-library.md](../rules/rule-library.md).

### 5. Wire to DAG

Declare `dependency_stage` in registry entry. The orchestrator resolves order automatically.
Do NOT add `if agent_id == "legal_compliance"` in `ReviewService`.

### 6. Add to Review Profiles

Update relevant profiles in `review_profiles/`:

```json
{ "id": "legal_compliance", "enabled": true }
```

or

```json
{ "id": "legal_compliance", "enabled": false }
```

### 7. Write Tests

Create `tests/unit/agents/test_legal_compliance.py`:

```python
def test_legal_compliance_agent_returns_contract(mock_provider):
    agent = LegalComplianceAgent(llm_provider=mock_provider, ...)
    result = agent.run(context=minimal_context())
    assert result.status == "completed"
    # validate contract fields
```

Minimum tests:
- Valid contract on success
- `status: failed` on exception
- `status: skipped` when required input missing

### 8. DB Migration (if new tables needed)

Add `CREATE TABLE IF NOT EXISTS` statement to `db/migrations/`. Idempotent.

### 9. Admin UI (usually automatic)

If the agent is data-driven (it is), the Admin UI should automatically list it.
Verify the agent appears in the Agent Registry UI. Do not add hardcoded UI code.

## What NOT to Do

- Do not inline prompt strings in the agent class
- Do not add `if agent_id == "..."` in `ReviewService`
- Do not modify any legacy file
- Do not hardcode model names in the agent

## Related Documents

- See: [../agents/agent-contract.md](../agents/agent-contract.md) for contract implementation
- See: [../agents/agent-registry.md](../agents/agent-registry.md) for registry schema
- See: [../prompts/prompt-schema.md](../prompts/prompt-schema.md) for prompt YAML format
- See: [testing.md](testing.md) for test patterns

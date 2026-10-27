# Prompt Lifecycle — NOW

## Purpose

Document the full lifecycle of a prompt version: creation, testing, evaluation, activation,
deprecation, and rollback.

## Core Rule

Every string that instructs an LLM lives in the Prompt Library. This includes:
- System role / persona instructions
- User message templates (with `{{variable}}` placeholders)
- Output schema / structured-output instructions
- Few-shot examples
- Chain-of-thought scaffolding

If it tells an LLM what to do, it belongs in the Prompt Library — not in Python code.

## Lifecycle Stages

```
1. Draft created (by engineer or Admin UI)
   status: draft

2. Tested (dry run against sample slides in Admin UI)
   status: draft

3. Evaluated (run against golden dataset via TruLens)
   status: draft — pending evaluation gate results

4. Gate passed
   status: draft — eligible for activation

5. Activated (promoted to active by authorized user)
   status: active
   Previous active version → status: deprecated

6. Deprecated (either replaced by new version, or manually)
   status: deprecated — immutable, never deleted
```

## Versioning Rules

- Version numbers are integers, monotonically increasing per `agent_id`.
- A prompt version is immutable once status moves from `draft` to `active`.
- To change a prompt: create a new version (draft), evaluate it, activate it.
- The old version is automatically deprecated when the new one is activated.
- Never reuse a version number.
- Every `agent_run` records `prompt_version_id` — findings are always traceable.

## Directory Layout (Seed Files)

```
prompts/
  content_agent/v1.yaml
  story_agent/v1.yaml
  customer_focus/v1.yaml
  cio_lens/v1.yaml
  critic/v1.yaml
  proposal_context/v1.yaml
  fix_agent/v1.yaml
```

Seed files are the source of truth for initial versions. Once loaded into the DB, they are immutable.
All subsequent edits happen through the Admin UI or API, which create new DB versions.

## PromptService API

```python
class PromptService:
    def get_active(self, agent_id: str, review_profile: str | None = None) -> PromptVersion:
        """
        Return active prompt for agent_id.
        If review_profile given, check for profile-scoped override first.
        Raises PromptNotFoundError if no active version exists.
        """

    def render(self, prompt_version: PromptVersion, variables: dict) -> RenderedPrompt:
        """
        Substitute {{variable}} placeholders in user_template.
        Raises PromptRenderError if a required variable is missing.
        """

    def create_version(self, agent_id: str, data: dict, created_by: str) -> PromptVersion:
        """Create new draft version. Does not activate it."""

    def activate(self, prompt_version_id: int, review_profile: str | None, activated_by: str) -> None:
        """Activate globally or for a specific Review Profile."""
```

## How an Agent Uses the Prompt Library

```python
# The ONLY permitted pattern for LLM-based agents
prompt_version = prompt_service.get_active(self.agent_id, review_profile)
rendered = prompt_service.render(prompt_version, {
    "slide_number": slide.number,
    "slide_title": slide.title,
    "slide_content": slide.content,
    "review_profile": review_profile,
})
response = llm_provider.complete(
    system=rendered.system_role,
    user=rendered.user_message,
    schema=rendered.output_schema,
)
```

## Admin UI Capabilities

| Screen | Capability |
|--------|-----------|
| Prompt List | All agents, current active version, last modified, status |
| Prompt Editor | Edit system role, user template, few-shots; save as new draft |
| Version History | All versions per agent, diff between any two |
| Activate | Promote draft to active (globally or per Review Profile) |
| Test / Dry Run | Run prompt version against a sample slide |
| Deprecate | Mark old versions deprecated (never delete) |

## Profile-Scoped Overrides

A Review Profile can specify a different prompt version for an agent:

```json
{
  "prompt_overrides": {
    "customer_focus": 7,
    "cio_lens": 3
  }
}
```

`PromptService.get_active(agent_id, review_profile)` checks for a profile-scoped override first,
then falls back to the global active version.

## Related Documents

- See: [prompt-schema.md](prompt-schema.md) for YAML and DB schema
- See: [prompt-evaluation.md](prompt-evaluation.md) for evaluation gates
- See: [../evaluation/evaluation-gates.md](../evaluation/evaluation-gates.md) for gate thresholds

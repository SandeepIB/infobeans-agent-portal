# Prompt Documents Index

| Document | Topic |
|----------|-------|
| [prompt-lifecycle.md](prompt-lifecycle.md) | Full prompt lifecycle: creation, evaluation, activation, deprecation |
| [prompt-schema.md](prompt-schema.md) | YAML seed format, DB schema, PromptService API |
| [prompt-evaluation.md](prompt-evaluation.md) | How prompts are evaluated before activation |
| [prompt-security.md](prompt-security.md) | PII, payload logging, and security controls |

## Core Rule

Every string that instructs an LLM lives in the Prompt Library. No exceptions.
No prompt strings in agent Python code. Ever.

## Quick Reference

- Get active prompt: `PromptService.get_active(agent_id, review_profile)`
- Render prompt: `PromptService.render(prompt_version, variables)`
- Create new version: `PromptService.create_version(agent_id, data, created_by)`
- Activate: `PromptService.activate(prompt_version_id, review_profile, activated_by)`

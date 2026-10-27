# System Overview

## Purpose

InfoBeans Agentic PPT Review Platform — a PowerPoint quality gate that evaluates customer-facing
presentations for brand compliance, content quality, storytelling, proposal coverage, and executive
readiness. Returns a readiness score, structured findings, and an auto-fixed PPT where safe.

## Evolution

Started as a mechanical brand-compliance validator (`rules.yaml` + `python-pptx` checks).
Being evolved into a configuration-driven, agentic platform:

- Deterministic orchestrator runs a registry of independent agents
- Agents: rule-based, LLM-based, or hybrid
- DAG execution: parallel where independent, sequential where dependent
- Review → Fix → Re-review loop
- All configuration in data (profiles, rules, prompts), not code

## Directory Map

```
app.py                 FROZEN — legacy routes + include_router(v2) mounts
db.py                  FROZEN — legacy `runs` table access
correct_pptx.py        FROZEN
rules.yaml             FROZEN — legacy mechanical rule set
static/index.html      FROZEN — legacy UI

validator/             FROZEN — mechanical brand checks, unchanged
  checks.py  core.py  llm_check.py  models.py  report_pdf.py  report_pptx.py  rules.py

frontend/              NEW — React/Vite: upload, progress, results, history, admin
agents/                NEW — ReviewAgent ABC + all agent implementations
llm/                   NEW — LLMProvider ABC + provider implementations
  provider.py              LLMProvider ABC + ProviderFactory
  providers/
    gateway_provider.py
    litellm_provider.py
    claude_provider.py
    groq_provider.py
    gemini_provider.py
    openai_provider.py
    mock_provider.py        deterministic test doubles, never calls real API
renderer/              NEW — SlideRenderer ABC, LibreOfficeRenderer, UnavailableRenderer, factory
prompts/               NEW — seed YAML files loaded into DB on first run
rule_library/          NEW — versioned rule YAML/JSON per domain
services/              NEW — ReviewService (orchestrator), PPTService, PromptService,
                             RuleService, ObservabilityService, FixService,
                             SlideDesignMatchService, CostGovernanceService
api/                   NEW — FastAPI v2 routers: review, prompts, rules, agents, observability, health
db/                    NEW — migrations + v2 repository + models
slide_templates/       NEW — reference PPT slides for design-match
```

## Key Constraints

- Legacy files are frozen — see `CLAUDE.md` Rule 1
- New code lives in new directories only
- The only permitted change to `app.py` is `include_router(...)` calls

## Related Documents

- See: [02-agent-dag.md](02-agent-dag.md) for execution model
- See: [06-llm-provider.md](06-llm-provider.md) for provider architecture
- See: [../development/adding-agent.md](../development/adding-agent.md) to add a new agent

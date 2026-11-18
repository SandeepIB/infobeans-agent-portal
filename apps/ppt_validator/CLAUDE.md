# CLAUDE.md — InfoBeans Agentic PPT Review Platform

Read this first. Then read [docs/INDEX.md](docs/INDEX.md) to find the right document for your task.
This file contains only mandatory rules. Detailed architecture is in `docs/`.

---

## What this is

A PowerPoint quality gate evolving from a mechanical brand validator into a governance-first
agentic Presentation Review Platform: deterministic orchestrator + independent LLM/rule agents +
Review → Fix → Re-review loop until decks are customer-ready.

See: [docs/architecture/01-system-overview.md](docs/architecture/01-system-overview.md)

---

## Mandatory Rules

Do not work around these. If a task requires breaking one, stop and flag it.

**1. Legacy is frozen.**
`app.py`, `db.py`, `validator/`, `correct_pptx.py`, `rules.yaml`, `static/index.html` — unchanged.
Only permitted change to `app.py`: adding `include_router(...)` for new v2 routers.

**2. Database changes are additive only.**
`CREATE TABLE IF NOT EXISTS`. Never alter or drop `runs`. Every migration is idempotent and safe to re-run.

**3. Agents never call LLMs directly.**
All model access through `LLMProvider` (`llm/provider.py`). Active provider from `LLM_PROVIDER` env var.
Direct HTTP calls to model APIs outside `llm/providers/` are bugs — fix them, do not extend them.
See: [docs/architecture/06-llm-provider.md](docs/architecture/06-llm-provider.md)

**4. Agents return the standard Agent Contract.**
No free text exits an agent boundary. Wrap LLM output in structured-output schema and validate before returning.
See: [docs/agents/agent-contract.md](docs/agents/agent-contract.md)

**5. Prompts come only from the Prompt Library.**
No prompt strings in agent code. All LLM instructions live in `prompts/` → DB `prompt_versions` → `PromptService`.
See: [docs/prompts/prompt-lifecycle.md](docs/prompts/prompt-lifecycle.md)

**6. Rules come only from the Rule Library.**
No thresholds or rule strings in agent code. Rule-based agents read from versioned YAML in `rule_library/`.
See: [docs/rules/rule-library.md](docs/rules/rule-library.md)

**7. Every finding has an action type.**
`action_type ∈ {AUTO_FIX, HUMAN_APPROVAL, RECOMMENDATION_ONLY}`.
Only `AUTO_FIX` may be mechanically applied. Never default to `AUTO_FIX` for ambiguous findings.
Never `AUTO_FIX` business commitments, scope changes, pricing, or contractual matters.

**8. Orchestrator is deterministic; agents are not orchestrators.**
The orchestrator decides execution order, retry, and human-approval routing.
LLMs do not decide which agents run or which findings are suppressed.
See: [docs/architecture/02-agent-dag.md](docs/architecture/02-agent-dag.md)

**9. Everything is versioned and auditable.**
Rules, prompts, and agents carry versions. Every agent run, LLM call, and fix is logged.
If a change isn't traceable, it is not done.
See: [docs/architecture/10-versioning-audit.md](docs/architecture/10-versioning-audit.md)

**10. Tests use MockProvider.**
No test may call a live LLM API. Set `LLM_PROVIDER=mock` in all test environments.
See: [docs/development/testing.md](docs/development/testing.md)

**11. Never expose secrets.**
API keys in `.env` (gitignored). Use `.env.example` with placeholder values for documentation.

**12. Observability never blocks the review pipeline.**
LangSmith and TruLens are side-channels. If either is unreachable, the review runs normally.
See: [docs/operations/observability.md](docs/operations/observability.md)

**13. Cost and token budgets are enforced.**
No uncontrolled LLM loops. Budget checked before execution begins.
See: [docs/operations/cost-governance.md](docs/operations/cost-governance.md)

**14. Never send unnecessary context to LLMs.**
Each agent receives only its required context scope. No agent receives the full PPT unless required.
See: [docs/architecture/context-optimization.md](docs/architecture/context-optimization.md)

**15. Use caching for deterministic reuse.**
Do not re-run unchanged prompts on unchanged inputs.
See: [docs/operations/caching.md](docs/operations/caching.md)

**16. Re-review only affected agents.**
After a fix, only invalidated agents rerun. Never rerun the entire pipeline for an unrelated change.
See: [docs/architecture/incremental-review.md](docs/architecture/incremental-review.md)

**17. Prompts and models require evaluation before activation.**
No prompt version becomes production-active without passing configured evaluation gates.
See: [docs/evaluation/evaluation-gates.md](docs/evaluation/evaluation-gates.md)

**18. Critical findings override numeric scores.**
A deck with a critical finding is BLOCKED regardless of its readiness score.
See: [docs/architecture/scoring.md](docs/architecture/scoring.md)

**19. Never silently suppress findings.**
Excluded slides and deduplicated findings are always logged with provenance.
See: [docs/architecture/exclusions.md](docs/architecture/exclusions.md) | [docs/architecture/finding-management.md](docs/architecture/finding-management.md)

**20. Human approval required for business/legal/scope/pricing/contractual decisions.**
These are never `AUTO_FIX`. Surface them as `HUMAN_APPROVAL`.

---

## Token Efficiency (mandatory for Claude CLI)

1. Read `CLAUDE.md` first, then `docs/INDEX.md`.
2. Identify the smallest relevant document set. Read only those.
3. Do not read all of `docs/` — use `docs/INDEX.md` to route to the right file.
4. Do not re-read unchanged documents within a session.
5. Prefer targeted `grep`/`find` over reading entire source files.
6. Use `MockProvider` for unit tests — never call real LLMs during testing.
7. Run the smallest sufficient test tier for the change being made.
8. Do not run full golden evaluations for unrelated code changes.
9. Stop investigating once sufficient evidence exists; do not over-explore.
10. Use existing abstractions — do not rediscover architecture already documented here.
11. Summarize discovered context internally before continuing to next steps.
12. Avoid duplicate LLM calls and repeated evaluation of unchanged inputs.

---

## Commands

```bash
uvicorn app:app --reload --port 8000    # backend
cd frontend && npm run dev               # frontend dev server
cd frontend && npm run build             # frontend prod (→ frontend/dist)
pytest tests/                            # unit tests (MockProvider only)
pytest tests/ -m integration            # integration tests
python db/migrate.py                     # additive DB migration (idempotent)
```

---

## Navigation

**Start here for any task:** [docs/INDEX.md](docs/INDEX.md)

## TOKEN EFFICIENCY

- Read only relevant documentation and source files.
- Never read the entire repository unless required.
- Never reread unchanged files.
- Prefer targeted searches and small file ranges.
- Never print complete files.
- Keep responses concise.
- Use deterministic code instead of LLMs where possible.
- Send minimum necessary context to LLMs.
- Reuse valid cached results.
- Avoid duplicate LLM calls.
- Use incremental re-review.
- Run the smallest sufficient test tier.
- Use MockProvider for unit tests.
- Do not run golden evaluations for unrelated changes.
- Use /compact when context becomes large.
- Use /clear when switching to an unrelated task.
- Correctness must never be sacrificed for token savings.

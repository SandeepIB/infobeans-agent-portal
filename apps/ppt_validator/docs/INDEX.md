# Documentation Index — InfoBeans Agentic PPT Review Platform

Read `CLAUDE.md` first, then use this table to find the right document for your task.
Do NOT read documents you do not need — that wastes context.

## Task → Document Routing

| Task | Read these documents |
|------|---------------------|
| Understand the overall system | [architecture/01-system-overview.md](architecture/01-system-overview.md) |
| Understand the Agent DAG | [architecture/02-agent-dag.md](architecture/02-agent-dag.md) |
| Add a new agent | [development/adding-agent.md](development/adding-agent.md), [agents/agent-contract.md](agents/agent-contract.md), [agents/agent-registry.md](agents/agent-registry.md) |
| Add a new LLM provider | [development/adding-provider.md](development/adding-provider.md), [architecture/06-llm-provider.md](architecture/06-llm-provider.md) |
| Add or change a rule | [rules/rule-library.md](rules/rule-library.md), [rules/rule-versioning.md](rules/rule-versioning.md) |
| Add or change a prompt | [prompts/prompt-lifecycle.md](prompts/prompt-lifecycle.md), [prompts/prompt-schema.md](prompts/prompt-schema.md) |
| Change the LLM provider configuration | [architecture/06-llm-provider.md](architecture/06-llm-provider.md) |
| Optimize cost or token usage | [operations/cost-governance.md](operations/cost-governance.md), [architecture/context-optimization.md](architecture/context-optimization.md) |
| Implement or understand caching | [operations/caching.md](operations/caching.md) |
| Write or run tests | [development/testing.md](development/testing.md) |
| Run evaluation or compare prompts | [evaluation/evaluation.md](evaluation/evaluation.md), [evaluation/evaluation-gates.md](evaluation/evaluation-gates.md) |
| Set up or check security/PII controls | [operations/security.md](operations/security.md) |
| Set up or check observability | [operations/observability.md](operations/observability.md) |
| Deploy the application | [operations/deployment.md](operations/deployment.md) |
| Work on the frontend | [development/frontend.md](development/frontend.md) |
| Work on the Fix Agent | [agents/fix-agent.md](agents/fix-agent.md), [architecture/09-fix-rereview.md](architecture/09-fix-rereview.md) |
| Work on the Proposal Context Agent | [agents/proposal-agent.md](agents/proposal-agent.md) |
| Work on the CIO Lens agent | [agents/cio-lens.md](agents/cio-lens.md) |
| Work on Slide Design Match | [agents/slide-design-match.md](agents/slide-design-match.md) |
| Work on the Critic agent | [agents/critic-agent.md](agents/critic-agent.md) |
| Understand scoring / readiness | [architecture/scoring.md](architecture/scoring.md) |
| Understand finding deduplication | [architecture/finding-management.md](architecture/finding-management.md) |
| Understand confidence calibration | [architecture/confidence.md](architecture/confidence.md) |
| Understand excluded slides | [architecture/exclusions.md](architecture/exclusions.md) |
| Understand reproducibility | [architecture/reproducibility.md](architecture/reproducibility.md) |
| Understand incremental re-review | [architecture/incremental-review.md](architecture/incremental-review.md) |
| Understand model routing | [architecture/model-routing.md](architecture/model-routing.md) |
| Understand concurrency / rate limits | [architecture/execution-controls.md](architecture/execution-controls.md) |
| Set up regression testing | [evaluation/regression-testing.md](evaluation/regression-testing.md) |
| Manage the golden dataset | [evaluation/golden-dataset.md](evaluation/golden-dataset.md) |
| Implement human feedback loop | [evaluation/human-feedback.md](evaluation/human-feedback.md) |
| Add a database migration | [development/database.md](development/database.md) |
| Understand versioning and audit trail | [architecture/10-versioning-audit.md](architecture/10-versioning-audit.md) |

## Architecture Documents

See [architecture/00-index.md](architecture/00-index.md) for the full architecture document list.

## Agent Documents

See [agents/00-index.md](agents/00-index.md) for the full agent specification list.

## Capability Implementation Status

| Capability | Status | Document |
|-----------|--------|----------|
| LLMProvider abstraction | NOW | [architecture/06-llm-provider.md](architecture/06-llm-provider.md) |
| Agent Contract | NOW | [agents/agent-contract.md](agents/agent-contract.md) |
| Prompt Library | NOW | [prompts/prompt-lifecycle.md](prompts/prompt-lifecycle.md) |
| Rule Library | NOW | [rules/rule-library.md](rules/rule-library.md) |
| MockProvider for tests | NOW | [development/testing.md](development/testing.md) |
| Cost tracking and token budgets | NOW | [operations/cost-governance.md](operations/cost-governance.md) |
| Context minimization per agent | NOW | [architecture/context-optimization.md](architecture/context-optimization.md) |
| LLM response caching | NOW | [operations/caching.md](operations/caching.md) |
| Basic evaluation (TruLens/LangSmith) | NOW | [evaluation/evaluation.md](evaluation/evaluation.md) |
| Evaluation gates | NOW | [evaluation/evaluation-gates.md](evaluation/evaluation-gates.md) |
| Advanced model routing | NEXT | [architecture/model-routing.md](architecture/model-routing.md) |
| Human feedback dataset | NEXT | [evaluation/human-feedback.md](evaluation/human-feedback.md) |
| Advanced regression platform | NEXT | [evaluation/regression-testing.md](evaluation/regression-testing.md) |
| Distributed execution | FUTURE | [architecture/12-scalability.md](architecture/12-scalability.md) |
| Multi-tenant isolation | FUTURE | [architecture/12-scalability.md](architecture/12-scalability.md) |

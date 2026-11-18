# Architecture Documents Index

| File | Topic |
|------|-------|
| [01-system-overview.md](01-system-overview.md) | What the system is; directory map |
| [02-agent-dag.md](02-agent-dag.md) | Agent execution DAG; orchestration rules |
| [03-agent-registry.md](03-agent-registry.md) | Agent Registry schema and examples |
| [04-agent-contract.md](04-agent-contract.md) | Standard Agent Contract (canonical reference) |
| [05-review-profiles.md](05-review-profiles.md) | Review Profile schema and configuration |
| [06-llm-provider.md](06-llm-provider.md) | LLMProvider ABC, supported providers, .env reference |
| [07-context-flow.md](07-context-flow.md) | How context flows between agents |
| [08-data-flow.md](08-data-flow.md) | End-to-end data lineage |
| [09-fix-rereview.md](09-fix-rereview.md) | Fix Agent and re-review loop |
| [10-versioning-audit.md](10-versioning-audit.md) | Versioning scheme and audit trail |
| [11-failure-recovery.md](11-failure-recovery.md) | Failure modes and recovery strategies |
| [12-scalability.md](12-scalability.md) | Scalability and multi-tenancy (FUTURE) |
| [model-routing.md](model-routing.md) | ModelRoutingService — route by agent/complexity/budget |
| [context-optimization.md](context-optimization.md) | Context minimization per agent |
| [execution-controls.md](execution-controls.md) | Concurrency, rate limits, circuit breakers |
| [incremental-review.md](incremental-review.md) | Re-review only affected agents after fix |
| [finding-management.md](finding-management.md) | Finding deduplication and provenance |
| [confidence.md](confidence.md) | Confidence calibration and handling |
| [scoring.md](scoring.md) | Score governance; critical finding override |
| [exclusions.md](exclusions.md) | Excluded slides; audit trail |
| [reproducibility.md](reproducibility.md) | Reproducing a review result |

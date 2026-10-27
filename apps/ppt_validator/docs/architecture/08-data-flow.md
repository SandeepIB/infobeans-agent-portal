# Data Flow

## Purpose

Document end-to-end data lineage from upload to readiness decision.

## Flow

```
1. Upload
   User → POST /api/v2/review/upload
   ├── PPTX file → stored as versioned artifact
   ├── Proposal Context (optional) → stored, versioned
   └── Reference Template PPT (optional) → stored, versioned

2. Review Request
   POST /api/v2/review/start
   ├── pptx_version_id
   ├── review_profile_id (+ version)
   ├── proposal_context_id (optional)
   └── reference_template_id (optional)

3. Extraction
   PPTService extracts:
   ├── Layout + design metadata per slide
   ├── Normalized slide content per slide
   ├── Speaker notes per slide
   └── Slide sequence metadata

4. Slide Design Match (if reference PPT provided)
   SlideDesignMatchService → matched_slide_indices list
   Stored in review context; agents check before emitting design findings

5. Agent Execution (DAG)
   ReviewService (orchestrator):
   ├── Reads Agent Registry + Review Profile
   ├── Builds execution plan
   ├── Distributes context slices to each agent
   ├── Collects AgentContract responses
   └── Logs each agent_run row

6. LLM Calls (within agents)
   LLMProvider.complete()
   ├── Check cache (cache_key = provider + model + prompt_version + input_hash)
   ├── If hit → return cached; log cache_hit
   ├── If miss → call provider; log llm_request row
   └── Store result in cache

7. Aggregation
   Aggregator:
   ├── Collects all agent scores + findings
   ├── Deduplicates findings (FindingCorrelationService)
   ├── Applies score weighting
   ├── Applies critical finding override
   └── Computes readiness: READY / REVIEW / BLOCKED

8. Output
   ReviewResult:
   ├── readiness: READY | REVIEW | BLOCKED
   ├── score: 0–100
   ├── findings: [canonical, deduplicated, action-typed]
   ├── proposal_coverage_matrix (if Proposal Agent ran)
   ├── agent_scores: per-agent breakdown
   └── audit_trail: all version IDs

9. Fix Loop (if AUTO_FIX findings exist and user triggers)
   FixService:
   ├── Applies only AUTO_FIX findings
   ├── Logs fix_operations rows
   ├── Produces new PPT version
   └── Triggers incremental re-review (only invalidated agents)
```

## Stored Artifacts

| Artifact | Table/Storage | Versioned |
|---------|--------------|-----------|
| PPT file | `ppt_uploads` | yes |
| Proposal Context | `proposal_contexts` | yes |
| Reference Template | `reference_templates` | yes |
| Review Profile | `review_profiles` | yes |
| Agent Registry entry | `agent_registry` | yes |
| Prompt version | `prompt_versions` | yes |
| Rule set version | `rule_versions` | yes |
| Agent run result | `agent_runs` | yes |
| LLM call | `llm_requests` | yes |
| Fix operation | `fix_operations` | yes |
| Evaluation result | `trulens_evaluations` | yes |

## Related Documents

- See: [10-versioning-audit.md](10-versioning-audit.md) for versioning scheme
- See: [../operations/caching.md](../operations/caching.md) for LLM cache
- See: [09-fix-rereview.md](09-fix-rereview.md) for fix loop
- See: [reproducibility.md](reproducibility.md) for reproducing a result

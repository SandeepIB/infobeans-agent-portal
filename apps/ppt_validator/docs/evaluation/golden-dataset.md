# Golden Dataset — NOW

## Purpose

A curated set of known PPT + expected findings pairs used for prompt evaluation and regression testing.
This is separate from the unit test suite.

## Dataset Structure

```
evaluation/
  golden/
    dataset_v1.yaml          # dataset metadata
    samples/
      sample_001/
        input.pptx           # sample PPT
        proposal_context.yaml  # optional
        review_profile.yaml
        expected_findings.json  # expected agent outputs
        notes.md             # why this sample exists
      sample_002/
        ...
```

## Dataset Metadata Schema

```yaml
dataset_version: 1
created_at: "2025-01-15"
description: "Initial golden dataset for Phase 1 agents"
samples:
  - id: sample_001
    description: "Strong customer proposal deck — expect high score, few findings"
    agents_covered: [content, story, customer_focus, proposal_context]
    review_profile: customer_presentation
  - id: sample_002
    description: "Deck with missing mandatory requirements — expect HUMAN_APPROVAL findings"
    agents_covered: [proposal_context]
    review_profile: customer_presentation
  - id: sample_003
    description: "Brand non-compliant deck — expect AUTO_FIX findings"
    agents_covered: [branding, template]
    review_profile: brand_audit
```

## Expected Findings Format

```json
{
  "sample_id": "sample_002",
  "agent_id": "proposal_context",
  "expected_score_range": [60, 80],
  "expected_findings": [
    {
      "slide": null,
      "severity": "HIGH",
      "category": "requirement_coverage",
      "action_type": "HUMAN_APPROVAL",
      "contains": "security architecture"    // finding description must contain this
    }
  ],
  "expected_no_findings": [
    { "category": "win_theme_coverage" }    // no findings expected in this category
  ]
}
```

## Dataset Versioning

- Dataset is versioned (`dataset_version: N`).
- New samples are added in new dataset versions.
- Evaluation results always record `dataset_version`.
- Do not modify existing samples — add new ones instead.

## Adding a Sample

1. Collect a real (anonymized) or synthetic PPT with known issues.
2. Manually verify expected findings.
3. Add to `evaluation/golden/samples/sample_NNN/`.
4. Update `dataset_v{N+1}.yaml` or increment dataset version.
5. Run evaluation to confirm the existing active prompts still pass gates.

## Usage in Evaluation

```bash
# Run evaluation against golden dataset
python evaluation/run_evaluation.py \
  --dataset evaluation/golden/dataset_v1.yaml \
  --prompt-version 5 \
  --agent content
```

## Security Note

Golden dataset PPTs may contain real customer data.
Anonymize all client names, financial figures, and PII before committing to the repository.

## Related Documents

- See: [evaluation.md](evaluation.md) for evaluation framework
- See: [evaluation-gates.md](evaluation-gates.md) for gate thresholds
- See: [regression-testing.md](regression-testing.md) for regression test usage

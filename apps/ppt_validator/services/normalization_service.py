"""Normalization service — deduplicates, resolves severity, and priority-ranks findings across agents."""
from __future__ import annotations
import re
from typing import Sequence
from agents.base import Finding, Severity, ActionType, Evidence


SEVERITY_ORDER = {
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


def _clean_text(text: str) -> str:
    """Normalize text for basic token-overlap similarity comparison."""
    return set(re.findall(r'\b[a-z0-9]{3,}\b', text.lower()))


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


class NormalizationService:
    """Standardizes, deduplicates, and priority-ranks cross-agent review findings."""

    def __init__(self, similarity_threshold: float = 0.25):
        self.similarity_threshold = similarity_threshold

    def normalize_and_deduplicate(self, raw_findings: Sequence[Finding]) -> list[Finding]:
        if not raw_findings:
            return []

        merged_clusters: list[list[Finding]] = []

        for item in raw_findings:
            tokens = _clean_text(f"{item.title} {item.description} {item.recommendation}")
            matched_cluster = None

            for cluster in merged_clusters:
                representative = cluster[0]
                # Match if on the exact same slide (or both slide 0)
                if representative.slide == item.slide:
                    rep_tokens = _clean_text(f"{representative.title} {representative.description} {representative.recommendation}")
                    sim = _jaccard_similarity(tokens, rep_tokens)
                    thresh = 0.15 if (item.slide > 0) else self.similarity_threshold
                    if sim >= thresh:
                        matched_cluster = cluster
                        break

            if matched_cluster:
                matched_cluster.append(item)
            else:
                merged_clusters.append([item])

        consolidated: list[Finding] = []
        for cluster in merged_clusters:
            consolidated.append(self._merge_cluster(cluster))

        # Priority Rank: Severity DESC -> Slide ASC -> Confidence DESC
        consolidated.sort(
            key=lambda f: (
                -SEVERITY_ORDER.get(f.severity, 1),
                f.slide if f.slide > 0 else 9999,
                -f.confidence
            )
        )

        return consolidated

    def _merge_cluster(self, cluster: list[Finding]) -> Finding:
        if len(cluster) == 1:
            return cluster[0]

        # Highest severity wins
        max_sev = max(cluster, key=lambda f: SEVERITY_ORDER.get(f.severity, 1)).severity

        # Highest confidence wins
        max_conf = max(f.confidence for f in cluster)

        # Combine unique categories
        categories = list(dict.fromkeys(f.category for f in cluster if f.category))
        merged_category = "/".join(categories)

        # Primary finding is the one with highest severity & confidence
        primary = max(cluster, key=lambda f: (SEVERITY_ORDER.get(f.severity, 1), f.confidence))

        # Combine evidence texts
        evidences = [f.evidence_text for f in cluster if f.evidence_text]
        merged_evidence = " | ".join(dict.fromkeys(evidences)) if evidences else primary.evidence_text

        # Combine recommendations if different
        recs = [f.recommendation for f in cluster if f.recommendation]
        merged_rec = " ".join(dict.fromkeys(recs)) if recs else primary.recommendation

        # Action type: AUTO_FIXABLE if any is AUTO_FIXABLE, else HUMAN_REVIEW_REQUIRED if any, else RECOMMENDATION_ONLY
        if any(f.action_type == ActionType.AUTO_FIXABLE for f in cluster):
            act_type = ActionType.AUTO_FIXABLE
        elif any(f.action_type == ActionType.HUMAN_REVIEW_REQUIRED for f in cluster):
            act_type = ActionType.HUMAN_REVIEW_REQUIRED
        else:
            act_type = ActionType.RECOMMENDATION_ONLY

        return Finding(
            id=primary.id,
            slide=primary.slide,
            severity=max_sev,
            category=merged_category,
            title=primary.title,
            description=primary.description,
            recommendation=merged_rec,
            confidence=max_conf,
            action_type=act_type,
            rule_id=primary.rule_id,
            evidence=merged_evidence,
        )

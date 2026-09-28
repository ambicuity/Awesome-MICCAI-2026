"""Transparent paper-quality metrics.

The quality module exposes per-paper dimensions, not a single opaque score.
Each dimension is documented and reproducible from the paper record.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict


def compute_paper_quality(
    has_abstract: bool,
    has_authors: bool,
    has_doi: bool,
    repository_count: int,
    evidence_strength: float,
    classification_confidence: float,
    published_at: str = "",
    now: datetime = None,
) -> Dict[str, float]:
    """Compute per-dimension quality metrics for a paper.

    All values are in ``[0, 1]``. They are NOT a single ranking score — they
    are diagnostic signals about record completeness.
    """
    now = now or datetime.now(timezone.utc)

    metadata_completeness = (
        (0.4 if has_abstract else 0.0)
        + (0.2 if has_authors else 0.0)
        + (0.2 if has_doi else 0.0)
        + (0.2 if repository_count > 0 else 0.0)
    )

    repository_accessibility = min(1.0, repository_count / 2.0)

    freshness_days = 365.0
    if published_at:
        try:
            ts = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            freshness_days = max(0.0, (now - ts).total_seconds() / 86400.0)
        except ValueError:
            pass
    freshness_score = max(0.0, 1.0 - freshness_days / 730.0)  # ~2 years half-life

    return {
        "metadata_completeness": round(metadata_completeness, 3),
        "repository_accessibility": round(repository_accessibility, 3),
        "conference_evidence_strength": round(float(evidence_strength), 3),
        "classification_confidence": round(float(classification_confidence), 3),
        "duplicate_risk": 0.0,  # filled in later by the dedup pass
        "freshness_days": round(freshness_days, 1),
        "freshness_score": round(freshness_score, 3),
    }
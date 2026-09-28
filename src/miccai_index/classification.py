"""Deterministic, multi-label taxonomy classifier.

The classifier turns a paper's textual fields into zero-or-more labels from
the configured taxonomy (``config/taxonomy.yaml``) along with a normalized
confidence score per label.

Design goals:

* Deterministic — same input produces the same output.
* Multi-label — a paper may be ``Segmentation`` and ``Reconstruction``.
* Title-weighted — title hits count more than abstract hits.
* Confidence per label — independent of other labels.
* Threshold-driven — labels are emitted only when weighted evidence crosses
  a per-label threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .config import TaxonomyConfig, TaxonomyLabel


@dataclass
class LabelAssignment:
    label_id: str
    label: str
    score: int
    confidence: float
    matched_patterns: List[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    title_hits: Dict[str, List[str]] = field(default_factory=dict)
    abstract_hits: Dict[str, List[str]] = field(default_factory=dict)
    assignments: List[LabelAssignment] = field(default_factory=list)
    unmatched: bool = False

    def by_label(self) -> Dict[str, LabelAssignment]:
        return {a.label_id: a for a in self.assignments}


def _compile_rules(label: TaxonomyLabel) -> List[Tuple[re.Pattern, int]]:
    return [(re.compile(rule.pattern, re.IGNORECASE), rule.weight) for rule in label.rules]


def _evidence_for_label(
    text: str,
    compiled: Sequence[Tuple[re.Pattern, int]],
    title_multiplier: int,
) -> Tuple[int, List[str]]:
    score = 0
    matches: List[str] = []
    for regex, weight in compiled:
        m = regex.search(text)
        if not m:
            continue
        if title_multiplier > 1:
            score += weight * title_multiplier
        else:
            score += weight
        matches.append(m.group(0))
    return score, matches


def classify_text(
    title: str,
    abstract: str,
    taxonomy: TaxonomyConfig,
    labels: Sequence[TaxonomyLabel],
    title_multiplier: int = 2,
    include_unmatched: bool = True,
) -> ClassificationResult:
    """Classify ``(title, abstract)`` against ``labels``.

    ``title_multiplier`` is applied to title hits. ``include_unmatched``
    adds a synthetic ``"general"`` label when nothing else matches.
    """
    title_l = (title or "").lower()
    abstract_l = (abstract or "").lower()

    result = ClassificationResult()
    for label in labels:
        compiled = _compile_rules(label)
        title_score, title_matches = _evidence_for_label(title_l, compiled, title_multiplier)
        abstract_score, abstract_matches = _evidence_for_label(abstract_l, compiled, 1)
        total = title_score + abstract_score

        result.title_hits[label.id] = title_matches
        result.abstract_hits[label.id] = abstract_matches

        if total < label.threshold:
            continue

        # Normalize confidence to [0, 1] using a soft cap. 2x threshold = 1.0.
        confidence = min(1.0, total / (2 * max(label.threshold, 1)))
        result.assignments.append(
            LabelAssignment(
                label_id=label.id,
                label=label.label,
                score=total,
                confidence=round(confidence, 3),
                matched_patterns=list(dict.fromkeys(title_matches + abstract_matches)),
            )
        )

    if include_unmatched and not result.assignments:
        result.unmatched = True
        # Synthesize a single General assignment with low confidence.
        result.assignments.append(
            LabelAssignment(
                label_id="general",
                label="General",
                score=0,
                confidence=0.1,
                matched_patterns=[],
            )
        )

    return result


def classify_tasks(title: str, abstract: str, taxonomy: TaxonomyConfig) -> ClassificationResult:
    return classify_text(title, abstract, taxonomy, taxonomy.tasks)


def classify_modalities(title: str, abstract: str, taxonomy: TaxonomyConfig) -> ClassificationResult:
    return classify_text(title, abstract, taxonomy, taxonomy.modalities)


def classify_methods(title: str, abstract: str, taxonomy: TaxonomyConfig) -> ClassificationResult:
    return classify_text(title, abstract, taxonomy, taxonomy.methods)


def classify_datasets(title: str, abstract: str, taxonomy: TaxonomyConfig) -> List[str]:
    """Return dataset labels matched anywhere in title/abstract."""
    text = f"{title or ''}\n{abstract or ''}".lower()
    matched: List[str] = []
    for dataset in taxonomy.datasets:
        for rule in dataset.rules:
            if re.search(rule.pattern, text, re.IGNORECASE):
                matched.append(dataset.label)
                break
    return matched


def assignment_confidences(result: ClassificationResult) -> Dict[str, float]:
    return {a.label_id: a.confidence for a in result.assignments}


def assignment_label_ids(result: ClassificationResult) -> List[str]:
    return [a.label_id for a in result.assignments]


def top_level_assignments(
    classifications: Iterable[Tuple[str, ClassificationResult]],
) -> Dict[str, List[LabelAssignment]]:
    """Group assignments by dimension (tasks/modalities/methods) for rendering."""
    out: Dict[str, List[LabelAssignment]] = {}
    for dimension, result in classifications:
        out[dimension] = result.assignments
    return out
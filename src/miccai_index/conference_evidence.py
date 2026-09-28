"""Structured conference-evidence detector.

For each candidate paper we collect zero or more evidence records, each with a
strength level (``EXPLICIT_STRONG`` … ``WEAK``). This lets downstream
pipelines decide:

* whether the paper is in scope for the chosen conference scope;
* why a paper was included or excluded (provenance).

The detector is deterministic and config-driven. It never guesses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .config import ConferenceConfig

# Order is significant: stronger evidence wins.
EVIDENCE_ORDER = (
    "EXPLICIT_STRONG",
    "EXPLICIT",
    "INFERRED",
    "WEAK",
    "UNKNOWN",
)
EVIDENCE_RANK = {level: idx for idx, level in enumerate(EVIDENCE_ORDER)}


@dataclass(frozen=True)
class ConferenceEvidence:
    source: str
    match: str
    strength: str
    year: Optional[int] = None


def _compiled_patterns(config: ConferenceConfig) -> List[Tuple[str, str, re.Pattern]]:
    """Return ``(level_id, pattern_text, compiled)`` tuples."""
    compiled: List[Tuple[str, str, re.Pattern]] = []
    for level in config.evidence_levels:
        for pattern in level.patterns:
            compiled.append((level.id, pattern, re.compile(pattern, re.IGNORECASE)))
    return compiled


def collect_conference_evidence(
    title: str,
    abstract: str,
    comment: Optional[str],
    config: ConferenceConfig,
) -> List[ConferenceEvidence]:
    """Collect structured evidence records about MICCAI affiliation.

    Sources of text are evaluated independently:

    * ``arxiv_title``
    * ``arxiv_abstract``
    * ``arxiv_comment`` (often contains the acceptance line)
    """
    evidence: List[ConferenceEvidence] = []
    sources: List[Tuple[str, str]] = [
        ("arxiv_title", title or ""),
        ("arxiv_abstract", abstract or ""),
        ("arxiv_comment", comment or ""),
    ]
    patterns = _compiled_patterns(config)

    for source_name, text in sources:
        if not text:
            continue
        for level_id, pattern_text, regex in patterns:
            match = regex.search(text)
            if not match:
                continue
            evidence.append(
                ConferenceEvidence(
                    source=source_name,
                    match=match.group(0),
                    strength=level_id,
                )
            )

    return evidence


def strongest_evidence(records: Iterable[ConferenceEvidence]) -> Optional[str]:
    rank = EVIDENCE_RANK
    best: Optional[str] = None
    for record in records:
        if best is None or rank[record.strength] < rank[best]:
            best = record.strength
    return best


def meets_scope_minimum(
    strongest: Optional[str],
    config: ConferenceConfig,
    scope_id: str,
) -> bool:
    """Return True if the strongest evidence satisfies the scope's minimum."""
    minimum = config.scope_minimum.get(scope_id, "WEAK")
    if strongest is None:
        return minimum == "WEAK"
    return EVIDENCE_RANK[strongest] <= EVIDENCE_RANK[minimum]


def is_target_miccai_paper(
    title: str,
    abstract: str,
    comment: Optional[str],
    arxiv_id: Optional[str],
    config: ConferenceConfig,
    scope_id: str,
    arxiv_year: Optional[int] = None,
) -> Tuple[bool, List[ConferenceEvidence]]:
    """Decide whether a paper belongs to the conference scope.

    Returns ``(in_scope, evidence_records)``.
    """
    evidence = collect_conference_evidence(title, abstract, comment, config)
    strongest = strongest_evidence(evidence)

    if strongest is None:
        return False, evidence

    if not meets_scope_minimum(strongest, config, scope_id):
        return False, evidence

    # For the year-specific scope, we additionally require that the paper
    # references the primary scope year explicitly — either in text or via the
    # arXiv ID year prefix.
    if scope_id == "miccai-2026":
        target_year = config.primary_scope_year
        # Comment is the strongest place to look for an explicit year.
        combined = f"{title or ''}\n{abstract or ''}\n{comment or ''}"
        year_match = re.search(
            r"\bmiccai\s*[-_ ]?\s*['’]?" + str(target_year) + r"\b",
            combined,
            re.IGNORECASE,
        )
        # Also accept short year form (e.g. MICCAI '26).
        short_match = re.search(
            r"\bmiccai\s*[-_ ]?\s*['’]?\d{2}\b",
            combined,
            re.IGNORECASE,
        )
        if year_match:
            return True, evidence
        if short_match:
            return True, evidence
        # Last resort: arXiv ID year prefix (2608 → 2026).
        if arxiv_year is not None and arxiv_year == target_year % 100:
            return True, evidence
        return False, evidence

    return True, evidence


def extract_year_from_arxiv_id(arxiv_id: Optional[str]) -> Optional[int]:
    """Return the two-digit year extracted from a modern arXiv ID, or ``None``."""
    if not arxiv_id:
        return None
    m = re.match(r"^(\d{2})\d{2}\.\d{4,5}$", arxiv_id)
    if not m:
        return None
    return int(m.group(1))


def evidence_to_dicts(records: Iterable[ConferenceEvidence]) -> List[dict]:
    """Serialize evidence records to plain dicts."""
    return [
        {
            "source": r.source,
            "match": r.match,
            "strength": r.strength,
            "year": r.year,
        }
        for r in records
    ]
"""End-to-end discovery + normalization + classification pipeline.

The ``DiscoveryPipeline`` ties together the source adapter, the conference
detector, the taxonomy classifier, and the repository normalizer. It produces
``PaperRecord`` instances that conform to ``schemas/paper.schema.json``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from .classification import (
    ClassificationResult,
    LabelAssignment,
    classify_datasets,
    classify_methods,
    classify_modalities,
    classify_tasks,
)
from .conference_evidence import (
    ConferenceEvidence,
    evidence_to_dicts,
    extract_year_from_arxiv_id,
    is_target_miccai_paper,
)
from .config import ConferenceConfig, SourcesConfig, TaxonomyConfig, ValidationConfig
from .errors import DiscoveryError, ValidationError
from .normalization import (
    RepositoryIdentity,
    extract_repository_links,
    parse_repository_url,
)
from .quality import compute_paper_quality
from .sources import ArxivSource

# Track detection patterns — independent of the previous keyword approach.
TRACK_PATTERNS = {
    "challenge": re.compile(
        r"\b(challenge|grand challenge|competition)\b", re.IGNORECASE
    ),
    "workshop": re.compile(
        r"\b(workshop|tutorial)\b", re.IGNORECASE
    ),
}

EVIDENCE_STRENGTH_SCORE = {
    "EXPLICIT_STRONG": 1.0,
    "EXPLICIT": 0.85,
    "INFERRED": 0.5,
    "WEAK": 0.2,
    "UNKNOWN": 0.0,
}


def infer_track(title: str, abstract: str, comment: str) -> str:
    """Return the track id for a paper based on textual evidence."""
    text = f"{title}\n{abstract}\n{comment}"
    if TRACK_PATTERNS["challenge"].search(text):
        return "challenge"
    if TRACK_PATTERNS["workshop"].search(text):
        return "workshop"
    return "main"


@dataclass
class PaperRecord:
    """In-memory paper record used between pipeline stages."""

    id: str
    title: str
    abstract: str
    identifiers: Dict[str, Any]
    venue: Dict[str, Any]
    track: str
    categories: List[str]
    modalities: List[str]
    methods: List[str]
    datasets: List[str]
    repositories: List[Dict[str, Any]]
    conference_evidence: List[Dict[str, Any]]
    confidence: Dict[str, float]
    provenance: Dict[str, Any]
    quality: Dict[str, float]
    timestamps: Dict[str, str]
    keywords: List[str] = field(default_factory=list)
    authors: List[Dict[str, Any]] = field(default_factory=list)
    note: Optional[str] = None  # human-readable flag, e.g. "uncertain"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": list(self.authors),
            "identifiers": self.identifiers,
            "venue": self.venue,
            "track": self.track,
            "categories": list(self.categories),
            "modalities": list(self.modalities),
            "methods": list(self.methods),
            "datasets": list(self.datasets),
            "repositories": list(self.repositories),
            "conference_evidence": list(self.conference_evidence),
            "confidence": dict(self.confidence),
            "provenance": self.provenance,
            "quality": dict(self.quality),
            "timestamps": dict(self.timestamps),
            "keywords": list(self.keywords),
        }


@dataclass
class PipelineResult:
    papers: List[PaperRecord]
    repositories: Dict[str, RepositoryIdentity]
    stats: Dict[str, int]
    warnings: List[str] = field(default_factory=list)
    source_snapshot_id: Optional[str] = None


class DiscoveryPipeline:
    """Run discovery + normalization + classification for one pipeline invocation."""

    def __init__(
        self,
        conference: ConferenceConfig,
        taxonomy: TaxonomyConfig,
        sources: SourcesConfig,
        validation: ValidationConfig,
        arxiv_source: ArxivSource,
        scope_id: str = "miccai-all-years",
    ) -> None:
        self.conference = conference
        self.taxonomy = taxonomy
        self.sources = sources
        self.validation = validation
        self.arxiv_source = arxiv_source
        self.scope_id = scope_id

    def _default_queries(self) -> List[str]:
        # Pull the queries off the configured arXiv source.
        for source in self.sources.sources:
            if source.id == self.arxiv_source.id:
                return list(source.default_queries)
        return []

    def _queries_for_scope(self) -> List[str]:
        base = self._default_queries()
        if self.scope_id == "miccai-2026":
            return [q for q in base if "2026" in q or "MICCAI 2026" in q] or [
                'ti:"MICCAI 2026"',
                'abs:"MICCAI 2026"',
                'co:"MICCAI 2026"',
            ]
        return base

    def run(self) -> PipelineResult:
        queries = self._queries_for_scope()
        records, source_metadata = self.arxiv_source.fetch(queries)

        stats = {
            "fetched_records": source_metadata.get("results_per_query", {})
            and sum(int(v) for v in source_metadata["results_per_query"].values()),
            "unique_records": 0,
            "filtered_non_target": 0,
            "filtered_track": 0,
            "filtered_no_code": 0,
            "accepted_records": 0,
            "duplicates_removed": 0,
            "uncertain_records": 0,
            "papers_added": 0,
            "papers_updated": 0,
            "papers_removed": 0,
        }
        if "fetched_records" not in stats or stats["fetched_records"] is None:
            stats["fetched_records"] = 0

        repositories: Dict[str, RepositoryIdentity] = {}
        seen_paper_ids: set = set()
        papers: List[PaperRecord] = []
        warnings: List[str] = []
        now = datetime.now(timezone.utc).isoformat()

        for record in records:
            stats["unique_records"] += 1
            arxiv_year = extract_year_from_arxiv_id(record.arxiv_id)

            in_scope, evidence = is_target_miccai_paper(
                title=record.title,
                abstract=record.summary,
                comment=record.comment,
                arxiv_id=record.arxiv_id,
                config=self.conference,
                scope_id=self.scope_id,
                arxiv_year=arxiv_year,
            )
            if not in_scope:
                stats["filtered_non_target"] += 1
                continue

            track = infer_track(record.title, record.summary, record.comment)
            repo_identities = extract_repository_links(
                f"{record.title}\n{record.summary}\n{record.comment}"
            )
            if not repo_identities:
                stats["filtered_no_code"] += 1
                continue

            # Apply track filter (CLI handles ``all``; here we filter explicitly).
            paper_id = f"arxiv:{record.arxiv_id}"
            if paper_id in seen_paper_ids:
                stats["duplicates_removed"] += 1
                continue
            seen_paper_ids.add(paper_id)

            repos_payload: List[Dict[str, Any]] = []
            for identity in repo_identities:
                repos_payload.append(
                    {
                        "id": identity.id,
                        "url": identity.url,
                        "host": identity.host,
                        "owner": identity.owner,
                        "name": identity.name,
                        "relationship": "official_implementation",
                        "confidence": "medium",
                        "evidence": [
                            "url_found_in_arxiv_metadata",
                        ],
                        "verification": {
                            "status": "unverified",
                            "checked_at": now,
                            "source": "pipeline",
                        },
                    }
                )
                repositories[identity.id] = identity

            tasks_result = classify_tasks(record.title, record.summary, self.taxonomy)
            modalities_result = classify_modalities(
                record.title, record.summary, self.taxonomy
            )
            methods_result = classify_methods(
                record.title, record.summary, self.taxonomy
            )
            datasets = classify_datasets(record.title, record.summary, self.taxonomy)
            categories = [a.label for a in tasks_result.assignments] or ["General"]

            confidence = {
                "overall": _overall_confidence(evidence),
                "tasks": {a.label_id: a.confidence for a in tasks_result.assignments},
                "modalities": {
                    a.label_id: a.confidence for a in modalities_result.assignments
                },
                "methods": {
                    a.label_id: a.confidence for a in methods_result.assignments
                },
            }
            uncertainty_note: Optional[str] = None
            if categories == ["General"] and confidence["overall"] < 0.4:
                stats["uncertain_records"] += 1
                uncertainty_note = "unmatched_taxonomy"

            quality = compute_paper_quality(
                has_abstract=bool(record.summary),
                has_authors=bool(record.authors),
                has_doi=False,
                repository_count=len(repos_payload),
                evidence_strength=confidence["overall"],
                classification_confidence=_mean_confidence(confidence),
                published_at=record.published,
            )

            venue = {
                "name": "MICCAI",
                "year": self.conference.primary_scope_year,
                "track": track,
            }

            keywords = _extract_keywords(record.title, record.summary)

            paper = PaperRecord(
                id=paper_id,
                title=record.title,
                abstract=record.summary,
                authors=[{"name": a} for a in record.authors],
                identifiers={
                    "arxiv": {
                        "id": record.arxiv_id,
                        "version": record.version,
                        "url": record.url,
                        "published": record.published,
                        "updated": record.updated,
                        "comment": record.comment,
                    }
                },
                venue=venue,
                track=track,
                categories=categories,
                modalities=[a.label for a in modalities_result.assignments],
                methods=[a.label for a in methods_result.assignments],
                datasets=datasets,
                repositories=repos_payload,
                conference_evidence=evidence_to_dicts(evidence),
                confidence=confidence,
                provenance={
                    "sources": ["arxiv"],
                    "fetched_at": now,
                    "snapshot_id": None,
                },
                quality=quality,
                timestamps={"created_at": now, "updated_at": now},
                keywords=keywords,
                note=uncertainty_note,
            )
            papers.append(paper)
            stats["accepted_records"] += 1

        # Sort papers deterministically: most recent first, then title.
        papers.sort(key=lambda p: (-_iso_timestamp(p.identifiers.get("arxiv", {}).get("published", "")), p.title.lower()))

        return PipelineResult(
            papers=papers,
            repositories=repositories,
            stats=stats,
            warnings=warnings,
            source_snapshot_id=None,
        )


def _overall_confidence(evidence: Sequence[ConferenceEvidence]) -> float:
    if not evidence:
        return 0.0
    return max(EVIDENCE_STRENGTH_SCORE.get(e.strength, 0.0) for e in evidence)


def _mean_confidence(confidence: Dict[str, Dict[str, float]]) -> float:
    values: List[float] = []
    for sub in confidence.values():
        if isinstance(sub, dict):
            values.extend(sub.values())
        elif isinstance(sub, (int, float)):
            values.append(float(sub))
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _iso_timestamp(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


_KEYWORD_STOPWORDS = {
    "a", "an", "the", "of", "on", "for", "and", "or", "in", "to", "with",
    "via", "using", "from", "by", "be", "is", "are", "we", "this", "that",
    "paper", "study", "approach", "method", "results", "model",
}


def _extract_keywords(title: str, abstract: str, max_keywords: int = 8) -> List[str]:
    text = f"{title or ''}. {abstract or ''}".lower()
    tokens = re.findall(r"[a-z][a-z0-9-]{2,}", text)
    seen: List[str] = []
    seen_set: set = set()
    for token in tokens:
        if token in _KEYWORD_STOPWORDS:
            continue
        if token in seen_set:
            continue
        seen_set.add(token)
        seen.append(token)
        if len(seen) >= max_keywords:
            break
    return seen
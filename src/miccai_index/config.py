"""Typed configuration objects loaded from YAML files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_loader import load_yaml_file
from .errors import ConfigurationError


@dataclass(frozen=True)
class ConferenceEvidenceLevel:
    id: str
    label: str
    description: str
    patterns: List[str]


@dataclass(frozen=True)
class ConferenceScope:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class Track:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class ConferenceConfig:
    name: str
    aliases: List[str]
    primary_scope_year: int
    supported_years: List[int]
    tracks: List[Track]
    repository_hosts: List[str]
    evidence_levels: List[ConferenceEvidenceLevel]
    scope_minimum: Dict[str, str]
    scopes: List[ConferenceScope]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class TaxonomyRule:
    pattern: str
    weight: int


@dataclass(frozen=True)
class TaxonomyLabel:
    id: str
    label: str
    threshold: int
    rules: List[TaxonomyRule]


@dataclass(frozen=True)
class TaxonomyConfig:
    version: str
    tasks: List[TaxonomyLabel]
    modalities: List[TaxonomyLabel]
    methods: List[TaxonomyLabel]
    datasets: List[TaxonomyLabel]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class SourceConfig:
    id: str
    label: str
    enabled: bool
    base_url: str
    timeout_seconds: int
    max_retries: int
    backoff_factor: int
    rate_limit_per_minute: int
    page_size: int
    max_results_per_query: int
    default_queries: List[str]


@dataclass(frozen=True)
class CacheConfig:
    enabled: bool
    directory: str
    ttl_seconds: int
    compress: bool


@dataclass(frozen=True)
class SourcesConfig:
    sources: List[SourceConfig]
    http_user_agent: str
    follow_redirects: bool
    verify_tls: bool
    cache: CacheConfig


@dataclass(frozen=True)
class HealthConfig:
    minimum_coverage_ratio: float
    max_category_drift_ratio: float
    max_repository_loss_ratio: float


@dataclass(frozen=True)
class ValidationConfig:
    supported_schema_versions: List[str]
    required_paper_fields: List[str]
    confidence_min_overall: float
    confidence_min_label: float
    health: HealthConfig
    category_order: List[str]
    required_markers: List[str]
    entry_format: str


def _resolve_path(base: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else base / p


def load_conference_config(path: str) -> ConferenceConfig:
    data = load_yaml_file(path)
    try:
        conference_block = data["conference"]
        tracks_block = data["tracks"]
        repo_hosts = data["repository_hosts"]
        evidence_levels = data["conference_evidence"]["levels"]
        scope_min = data["conference_evidence"]["scope_minimum"]
        scopes_block = data["scopes"]
    except KeyError as exc:
        raise ConfigurationError(f"Missing key in conference config: {exc}") from exc

    tracks = [
        Track(
            id=t["id"],
            label=t["label"],
            description=t["description"],
        )
        for t in tracks_block
    ]
    evidence = [
        ConferenceEvidenceLevel(
            id=lvl["id"],
            label=lvl["label"],
            description=lvl["description"],
            patterns=list(lvl["patterns"]),
        )
        for lvl in evidence_levels
    ]
    scopes = [
        ConferenceScope(id=s["id"], label=s["label"], description=s["description"])
        for s in scopes_block
    ]

    return ConferenceConfig(
        name=conference_block["name"],
        aliases=list(conference_block["aliases"]),
        primary_scope_year=int(conference_block["primary_scope_year"]),
        supported_years=[int(y) for y in conference_block["supported_years"]],
        tracks=tracks,
        repository_hosts=list(repo_hosts),
        evidence_levels=evidence,
        scope_minimum={str(k): str(v) for k, v in scope_min.items()},
        scopes=scopes,
        raw=data,
    )


def load_taxonomy_config(path: str) -> TaxonomyConfig:
    data = load_yaml_file(path)
    try:
        version = data["taxonomy_version"]
        tasks = data["tasks"]
        modalities = data["modalities"]
        methods = data["methods"]
        datasets = data["datasets"]
    except KeyError as exc:
        raise ConfigurationError(f"Missing key in taxonomy config: {exc}") from exc

    def _parse(labels: List[Dict[str, Any]]) -> List[TaxonomyLabel]:
        parsed: List[TaxonomyLabel] = []
        for label in labels:
            raw_rules = label.get("rules") or label.get("patterns") or []
            rules: List[TaxonomyRule] = []
            for entry in raw_rules:
                if isinstance(entry, str):
                    rules.append(TaxonomyRule(pattern=entry, weight=1))
                elif isinstance(entry, dict):
                    rules.append(
                        TaxonomyRule(
                            pattern=entry["pattern"],
                            weight=int(entry.get("weight", 1)),
                        )
                    )
            threshold = int(label.get("threshold", 1))
            parsed.append(
                TaxonomyLabel(
                    id=label["id"],
                    label=label["label"],
                    threshold=threshold,
                    rules=rules,
                )
            )
        return parsed

    return TaxonomyConfig(
        version=str(version),
        tasks=_parse(tasks),
        modalities=_parse(modalities),
        methods=_parse(methods),
        datasets=_parse(datasets),
        raw=data,
    )


def load_sources_config(path: str) -> SourcesConfig:
    data = load_yaml_file(path)
    sources: List[SourceConfig] = []
    for s in data.get("sources", []):
        net = s["network"]
        pag = s["pagination"]
        sources.append(
            SourceConfig(
                id=s["id"],
                label=s["label"],
                enabled=bool(s["enabled"]),
                base_url=s["base_url"],
                timeout_seconds=int(net["timeout_seconds"]),
                max_retries=int(net["max_retries"]),
                backoff_factor=int(net["backoff_factor"]),
                rate_limit_per_minute=int(net["rate_limit_per_minute"]),
                page_size=int(pag["page_size"]),
                max_results_per_query=int(pag["max_results_per_query"]),
                default_queries=list(s["default_queries"]),
            )
        )
    http = data["http_defaults"]
    cache_block = data["cache"]
    cache = CacheConfig(
        enabled=bool(cache_block["enabled"]),
        directory=str(cache_block["directory"]),
        ttl_seconds=int(cache_block["ttl_seconds"]),
        compress=bool(cache_block["compress"]),
    )
    return SourcesConfig(
        sources=sources,
        http_user_agent=str(http["user_agent"]),
        follow_redirects=bool(http["follow_redirects"]),
        verify_tls=bool(http["verify_tls"]),
        cache=cache,
    )


def load_validation_config(path: str) -> ValidationConfig:
    data = load_yaml_file(path)
    try:
        validation = data["validation"]
        health = data["health"]
        readme = data["readme"]
    except KeyError as exc:
        raise ConfigurationError(f"Missing key in validation config: {exc}") from exc

    confidence = validation["confidence"]
    return ValidationConfig(
        supported_schema_versions=list(validation["supported_schema_versions"]),
        required_paper_fields=list(validation["required_paper_fields"]),
        confidence_min_overall=float(confidence["min_overall"]),
        confidence_min_label=float(confidence["min_label"]),
        health=HealthConfig(
            minimum_coverage_ratio=float(health["minimum_coverage_ratio"]),
            max_category_drift_ratio=float(health["max_category_drift_ratio"]),
            max_repository_loss_ratio=float(health["max_repository_loss_ratio"]),
        ),
        category_order=list(readme["category_order"]),
        required_markers=list(readme["required_markers"]),
        entry_format=str(readme["entry_format"]),
    )


def default_config_paths(repo_root: Optional[Path] = None) -> Dict[str, str]:
    root = (repo_root or Path.cwd()).resolve()
    return {
        "conference": str(root / "config" / "conference.yaml"),
        "taxonomy": str(root / "config" / "taxonomy.yaml"),
        "sources": str(root / "config" / "sources.yaml"),
        "validation": str(root / "config" / "validation.yaml"),
    }


def load_all(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    paths = default_config_paths(repo_root)
    return {
        "conference": load_conference_config(paths["conference"]),
        "taxonomy": load_taxonomy_config(paths["taxonomy"]),
        "sources": load_sources_config(paths["sources"]),
        "validation": load_validation_config(paths["validation"]),
        "paths": paths,
    }
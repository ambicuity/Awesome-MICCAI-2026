"""Command-line interface for the MICCAI index pipeline.

Subcommands:

* ``discover``  run discovery only and emit raw records (debugging).
* ``normalize`` run discovery + normalization; write canonical JSONL to ``data/``.
* ``classify``  re-run taxonomy classification over an existing ``papers.json`` ledger.
* ``validate``  validate existing data products and ``README.md``.
* ``render``    render ``README.md`` from ``data/papers.json``.
* ``build``     run the full pipeline (discover → normalize → validate → render → products).
* ``report``    print analytics over the existing dataset.
* ``update``    alias for ``build`` (matches the historical Makefile target).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .cache import FileCache
from .changelog import diff_paper_records, write_changelog
from .config import (
    default_config_paths,
    load_all,
    load_conference_config,
    load_sources_config,
    load_taxonomy_config,
    load_validation_config,
)
from .config_loader import load_yaml_file
from .discovery import DiscoveryPipeline
from .errors import ConfigurationError, DiscoveryError, IndexError_, ValidationError
from .rendering.data_products import build_dist_products, write_dist_products
from .rendering.readme import update_readme_markers
from .sources import ArxivSource
from .storage import default_data_paths, read_jsonl, write_jsonl
from .validation import (
    load_schema,
    raise_on_errors,
    referential_integrity_check,
    validate_against_schema,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="miccai-index",
        description="MICCAI research discovery pipeline",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--config-dir",
        default="config",
        help="Directory containing the YAML configuration files.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip network requests; use cached data only.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the pipeline but do not write any output files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--scope",
        choices=["miccai-2026", "miccai-all-years"],
        default="miccai-all-years",
        help="Conference scope.",
    )
    common.add_argument(
        "--mode",
        choices=["strict", "broad"],
        default="broad",
        help="Discovery strictness.",
    )
    common.add_argument(
        "--tracks",
        choices=["main", "workshops", "challenges", "all"],
        default="all",
        help="Track filter.",
    )

    sub.add_parser("discover", parents=[common], help="Run discovery only.")
    sub.add_parser("normalize", parents=[common], help="Run discovery + normalization.")
    sub.add_parser("classify", parents=[common], help="Re-run classification over an existing dataset.")
    sub.add_parser("validate", parents=[common], help="Validate existing data products.")
    sub.add_parser("render", parents=[common], help="Render README from canonical data.")
    sub.add_parser("build", parents=[common], help="Run the full pipeline.")
    sub.add_parser("update", parents=[common], help="Alias for build.")
    sub.add_parser("report", parents=[common], help="Print analytics over existing dataset.")

    return parser


def _load_configs(config_dir: str) -> dict:
    base = Path(config_dir).resolve()
    paths = {
        "conference": str(base / "conference.yaml"),
        "taxonomy": str(base / "taxonomy.yaml"),
        "sources": str(base / "sources.yaml"),
        "validation": str(base / "validation.yaml"),
    }
    return {
        "conference": load_conference_config(paths["conference"]),
        "taxonomy": load_taxonomy_config(paths["taxonomy"]),
        "sources": load_sources_config(paths["sources"]),
        "validation": load_validation_config(paths["validation"]),
        "paths": paths,
    }


def _make_arxiv_source(sources_config, cache_dir: str) -> ArxivSource:
    arxiv_cfg = next(s for s in sources_config.sources if s.id == "arxiv")
    cache = FileCache(
        directory=cache_dir or arxiv_cfg.base_url,
        ttl_seconds=sources_config.cache.ttl_seconds,
    )
    # Reuse the configured cache directory when provided.
    cache.directory = Path(cache_dir or sources_config.cache.directory)
    cache.directory.mkdir(parents=True, exist_ok=True)
    return ArxivSource(arxiv_cfg, cache=cache)


def _validate_data(papers: list, schemas_dir: str, config_dir: str) -> List[str]:
    errors: List[str] = []
    paper_schema = load_schema(Path(schemas_dir) / "paper.schema.json")
    repo_schema_path = Path(schemas_dir) / "repository.schema.json"
    for idx, record in enumerate(papers):
        for err in validate_against_schema(record, paper_schema):
            errors.append(f"papers.jsonl[{idx}]: {err}")

    taxonomy = load_taxonomy_config(Path(config_dir) / "taxonomy.yaml")
    known = [t.label for t in taxonomy.tasks] + [t.label for t in taxonomy.modalities] + [t.label for t in taxonomy.methods]
    for err in referential_integrity_check(papers, known_categories=known):
        errors.append(err)

    # Validate repositories too if the schema file exists.
    if repo_schema_path.exists():
        repo_schema = load_schema(str(repo_schema_path))
        repo_path = Path(config_dir).parent / "data" / "repositories.jsonl"
        if repo_path.exists():
            import json as _json
            with open(repo_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        repo = _json.loads(line)
                    except _json.JSONDecodeError:
                        errors.append(f"repositories.jsonl:{line_no}: invalid JSON")
                        continue
                    for err in validate_against_schema(repo, repo_schema):
                        errors.append(f"repositories.jsonl[{line_no}]: {err}")
    return errors


def cmd_discover(args, configs, **_) -> int:
    arxiv = _make_arxiv_source(configs["sources"], args.cache_dir)
    if args.offline:
        arxiv.cache.directory.mkdir(parents=True, exist_ok=True)
        # In offline mode we still trust the cache: nothing to do here.
        print(f"[discover] offline mode, cache dir = {arxiv.cache.directory}")
        return 0

    queries = arxiv.config.default_queries
    if args.scope == "miccai-2026":
        queries = [q for q in queries if "2026" in q or "MICCAI 2026" in q] or queries
    records, meta = arxiv.fetch(queries)
    print(json.dumps({
        "fetched": sum(int(v) for v in meta["results_per_query"].values()),
        "unique": len(records),
        "results_per_query": meta["results_per_query"],
        "failed_queries": meta["failed_queries"],
    }, indent=2))
    return 0


def cmd_normalize(args, configs, *, data_paths, **_) -> int:
    if args.offline:
        print("[normalize] offline mode; skipping network fetch.")
        return 0
    arxiv = _make_arxiv_source(configs["sources"], data_paths["snapshots"])
    pipeline = DiscoveryPipeline(
        conference=configs["conference"],
        taxonomy=configs["taxonomy"],
        sources=configs["sources"],
        validation=configs["validation"],
        arxiv_source=arxiv,
        scope_id=args.scope,
    )
    result = pipeline.run()
    papers_dicts = [p.to_dict() for p in result.papers]
    if args.dry_run:
        print(json.dumps(result.stats, indent=2))
        return 0
    write_jsonl(papers_dicts, data_paths["papers"])
    repo_dicts = [
        {
            "id": r.id, "host": r.host, "owner": r.owner, "name": r.name, "url": r.url,
            "timestamps": {
                "first_seen": result.papers[0].timestamps["created_at"] if result.papers else "",
                "last_seen": result.papers[0].timestamps["created_at"] if result.papers else "",
            },
        }
        for r in result.repositories.values()
    ]
    write_jsonl(repo_dicts, data_paths["repositories"])
    print(f"[normalize] wrote {len(papers_dicts)} papers, {len(repo_dicts)} repositories.")
    return 0


def cmd_render(args, configs, *, data_paths, **_) -> int:
    papers_dicts = read_jsonl(data_paths["papers"])
    from .discovery import PaperRecord
    papers = [_dict_to_paper(d) for d in papers_dicts]
    if not papers:
        print("[render] no papers found in dataset; nothing to render.")
        return 1
    stats = {"fetched_records": 0, "unique_records": 0, "filtered_non_target": 0, "filtered_track": 0, "filtered_no_code": 0, "uncertain_records": 0}
    counts = update_readme_markers(
        "README.md",
        papers,
        stats,
        args.scope,
        args.mode,
        args.tracks,
    )
    print("[render] updated README.md categories:", counts)
    return 0


def cmd_validate(args, configs, *, data_paths, **_) -> int:
    papers_dicts = read_jsonl(data_paths["papers"])
    errors = _validate_data(papers_dicts, data_paths["schemas"], configs["paths"]["taxonomy"].rsplit("/", 1)[0])
    if errors:
        print("[validate] FAILED with the following issues:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"[validate] OK ({len(papers_dicts)} papers checked).")
    return 0


def cmd_build(args, configs, *, data_paths, **_) -> int:
    if args.offline:
        print("[build] offline mode; loading existing data products.")
        return cmd_render(args, configs, data_paths=data_paths)
    arxiv = _make_arxiv_source(configs["sources"], data_paths["snapshots"])
    pipeline = DiscoveryPipeline(
        conference=configs["conference"],
        taxonomy=configs["taxonomy"],
        sources=configs["sources"],
        validation=configs["validation"],
        arxiv_source=arxiv,
        scope_id=args.scope,
    )
    result = pipeline.run()
    paper_dicts = [p.to_dict() for p in result.papers]

    # Diff against the existing dataset to emit a changelog.
    previous_dicts = read_jsonl(data_paths["papers"])
    previous_by_id = {p["id"]: p for p in previous_dicts if "id" in p}
    current_by_id = {p["id"]: p for p in paper_dicts}
    events = diff_paper_records(previous_by_id, current_by_id)
    changelog_path = str(Path(data_paths["papers"]).parent / "changelog.jsonl")
    write_changelog(events, changelog_path)

    # Health check: if discovery looks degraded, refuse to overwrite good data.
    from .health import evaluate_run_health
    prev_categories: Dict[str, int] = {}
    for paper in previous_dicts:
        for cat in paper.get("categories", []) or []:
            prev_categories[cat] = prev_categories.get(cat, 0) + 1
    prev_hosts: Dict[str, int] = {}
    for paper in previous_dicts:
        for repo in paper.get("repositories", []) or []:
            host = repo.get("host")
            if host:
                prev_hosts[host] = prev_hosts.get(host, 0) + 1

    current_categories: Dict[str, int] = {}
    for paper in paper_dicts:
        for cat in paper.get("categories", []) or []:
            current_categories[cat] = current_categories.get(cat, 0) + 1
    current_hosts: Dict[str, int] = {}
    for paper in paper_dicts:
        for repo in paper.get("repositories", []) or []:
            host = repo.get("host")
            if host:
                current_hosts[host] = current_hosts.get(host, 0) + 1

    health = evaluate_run_health(
        previous_paper_count=len(previous_dicts),
        current_paper_count=len(paper_dicts),
        previous_categories=prev_categories,
        current_categories=current_categories,
        previous_repo_hosts=prev_hosts,
        current_repo_hosts=current_hosts,
        config=configs["validation"],
    )
    print(
        f"[build] health: coverage_ratio={health.coverage_ratio:.3f} "
        f"category_drift_ratio={health.category_drift_ratio:.3f} "
        f"repository_loss_ratio={health.repository_loss_ratio:.3f}"
    )
    if not health.healthy:
        print("[build] HEALTH CHECK FAILED; preserving previous canonical dataset.")
        for issue in health.issues:
            print(f"  - {issue}")
        # Changelog is still emitted so maintainers can audit the diff, but the
        # canonical dataset is not overwritten.
        return 2

    if not args.dry_run:
        write_jsonl(paper_dicts, data_paths["papers"])
        repo_dicts = [
            {
                "id": r.id, "host": r.host, "owner": r.owner, "name": r.name, "url": r.url,
                "timestamps": {
                    "first_seen": paper_dicts[0]["timestamps"]["created_at"] if paper_dicts else "",
                    "last_seen": paper_dicts[0]["timestamps"]["created_at"] if paper_dicts else "",
                },
                "verification": {"status": "unverified", "checked_at": "", "source": ""},
            }
            for r in result.repositories.values()
        ]
        write_jsonl(repo_dicts, data_paths["repositories"])

        papers = [_dict_to_paper(d) for d in paper_dicts]
        update_readme_markers(
            "README.md",
            papers,
            result.stats,
            args.scope,
            args.mode,
            args.tracks,
        )

        products = build_dist_products(
            papers=papers,
            repositories=result.repositories,
            stats={**result.stats, "papers_added_since_last_run": sum(1 for e in events if e.type == "paper_added"),
                   "papers_removed_since_last_run": sum(1 for e in events if e.type == "paper_removed"),
                   "papers_updated_since_last_run": sum(1 for e in events if e.type == "paper_updated")},
            conference={"name": configs["conference"].name, "year": configs["conference"].primary_scope_year},
            schema_version="1.0.0",
            index_version=__version__,
        )
        write_dist_products(products, data_paths["dist"])

    # Final validation.
    errors = _validate_data(paper_dicts, data_paths["schemas"], configs["paths"]["taxonomy"].rsplit("/", 1)[0])
    if errors:
        print("[build] VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[build] completed:", json.dumps({**result.stats, "events": len(events)}, indent=2))
    return 0


def cmd_classify(args, configs, *, data_paths, **_) -> int:
    papers_dicts = read_jsonl(data_paths["papers"])
    if not papers_dicts:
        print("[classify] no papers found; nothing to classify.")
        return 1
    from .classification import classify_tasks, classify_modalities, classify_methods, classify_datasets
    from .discovery import PaperRecord
    taxonomy = configs["taxonomy"]
    updated: List[dict] = []
    for d in papers_dicts:
        title = d.get("title", "")
        abstract = d.get("abstract", "")
        tasks = classify_tasks(title, abstract, taxonomy)
        modalities = classify_modalities(title, abstract, taxonomy)
        methods = classify_methods(title, abstract, taxonomy)
        datasets = classify_datasets(title, abstract, taxonomy)
        d["categories"] = [a.label for a in tasks.assignments] or ["General"]
        d["modalities"] = [a.label for a in modalities.assignments]
        d["methods"] = [a.label for a in methods.assignments]
        d["datasets"] = datasets
        d.setdefault("confidence", {})
        d["confidence"]["tasks"] = {a.label_id: a.confidence for a in tasks.assignments}
        d["confidence"]["modalities"] = {a.label_id: a.confidence for a in modalities.assignments}
        d["confidence"]["methods"] = {a.label_id: a.confidence for a in methods.assignments}
        updated.append(d)
    if not args.dry_run:
        write_jsonl(updated, data_paths["papers"])
    print(f"[classify] re-classified {len(updated)} papers.")
    return 0


def cmd_report(args, configs, *, data_paths, **_) -> int:
    papers_dicts = read_jsonl(data_paths["papers"])
    if not papers_dicts:
        print("[report] no papers found.")
        return 0
    from collections import Counter
    cat_counter = Counter(c for p in papers_dicts for c in p.get("categories", []))
    mod_counter = Counter(m for p in papers_dicts for m in p.get("modalities", []))
    method_counter = Counter(m for p in papers_dicts for m in p.get("methods", []))
    track_counter = Counter(p.get("track", "unknown") for p in papers_dicts)
    host_counter = Counter(r["host"] for p in papers_dicts for r in p.get("repositories", []))
    print(json.dumps({
        "papers_total": len(papers_dicts),
        "categories": dict(cat_counter.most_common()),
        "modalities": dict(mod_counter.most_common()),
        "methods": dict(method_counter.most_common()),
        "tracks": dict(track_counter.most_common()),
        "repository_hosts": dict(host_counter.most_common()),
    }, indent=2))
    return 0


def _dict_to_paper(d: dict):
    from .discovery import PaperRecord
    return PaperRecord(
        id=d["id"],
        title=d["title"],
        abstract=d.get("abstract", ""),
        authors=d.get("authors", []) or [],
        identifiers=d.get("identifiers", {}),
        venue=d.get("venue", {}),
        track=d.get("track", "unknown"),
        categories=d.get("categories", []) or [],
        modalities=d.get("modalities", []) or [],
        methods=d.get("methods", []) or [],
        datasets=d.get("datasets", []) or [],
        repositories=d.get("repositories", []) or [],
        conference_evidence=d.get("conference_evidence", []) or [],
        confidence=d.get("confidence", {}) or {},
        provenance=d.get("provenance", {}) or {},
        quality=d.get("quality", {}) or {},
        timestamps=d.get("timestamps", {}) or {},
        keywords=d.get("keywords", []) or [],
        note=None,
    )


COMMANDS = {
    "discover": cmd_discover,
    "normalize": cmd_normalize,
    "classify": cmd_classify,
    "validate": cmd_validate,
    "render": cmd_render,
    "build": cmd_build,
    "update": cmd_build,
    "report": cmd_report,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        configs = _load_configs(args.config_dir)
    except (ConfigurationError, FileNotFoundError) as exc:
        print(f"Configuration error: {exc}")
        return 2

    data_paths = default_data_paths()
    if not args.dry_run:
        Path(data_paths["papers"]).parent.mkdir(parents=True, exist_ok=True)
        Path(data_paths["dist"]).mkdir(parents=True, exist_ok=True)
        Path(data_paths["snapshots"]).mkdir(parents=True, exist_ok=True)

    handler = COMMANDS[args.command]
    args.cache_dir = data_paths["snapshots"]
    try:
        return handler(args, configs, data_paths=data_paths)
    except IndexError_ as exc:
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
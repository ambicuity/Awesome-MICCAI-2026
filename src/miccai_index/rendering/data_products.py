"""Machine-readable data products for downstream consumers.

Generated under ``dist/``:

* ``papers.json``              canonical paper records
* ``papers.jsonl``             canonical paper records (JSONL)
* ``repositories.json``        canonical repository records
* ``categories.json``          per-category counts
* ``modalities.json``          per-modality counts
* ``methods.json``             per-method counts
* ``datasets.json``            per-dataset counts
* ``statistics.json``          aggregate pipeline statistics
* ``search-index.json``        minimal client-side search index
* ``sitemap.json``             flat list of public URLs
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Sequence

from ..discovery import PaperRecord
from ..normalization import RepositoryIdentity

DIST_FILES = (
    "papers.json",
    "papers.jsonl",
    "repositories.json",
    "categories.json",
    "modalities.json",
    "methods.json",
    "datasets.json",
    "statistics.json",
    "search-index.json",
)


@dataclass
class DistProduct:
    filename: str
    payload: Any


def _count_dict(items: Iterable[str]) -> dict:
    return dict(sorted(Counter(items).items(), key=lambda kv: (-kv[1], kv[0])))


def build_dist_products(
    papers: Sequence[PaperRecord],
    repositories: dict[str, RepositoryIdentity],
    stats: dict,
    conference: dict,
    schema_version: str,
    index_version: str,
) -> List[DistProduct]:
    paper_dicts = [p.to_dict() for p in papers]
    repo_dicts = [
        {
            "id": r.id,
            "host": r.host,
            "owner": r.owner,
            "name": r.name,
            "url": r.url,
            "papers": [p.id for p in papers if any(rr.get("id") == r.id for rr in p.repositories)],
        }
        for r in repositories.values()
    ]

    # Counts.
    categories = _count_dict(
        c for p in papers for c in p.categories
    )
    modalities = _count_dict(
        m for p in papers for m in p.modalities
    )
    methods = _count_dict(
        m for p in papers for m in p.methods
    )
    datasets = _count_dict(d for p in papers for d in p.datasets)

    statistics = {
        "papers_total": len(papers),
        "papers_with_code": sum(1 for p in papers if p.repositories),
        "papers_unique": len({p.id for p in papers}),
        "papers_uncertain": sum(1 for p in papers if p.note == "unmatched_taxonomy"),
        "papers_by_track": _count_dict(p.track for p in papers),
        "papers_by_repository_host": _count_dict(
            r["host"] for p in papers for r in p.repositories
        ),
        **stats,
    }

    search_index = [
        {
            "id": p.id,
            "title": p.title,
            "track": p.track,
            "categories": p.categories,
            "modalities": p.modalities,
            "methods": p.methods,
            "datasets": p.datasets,
            "year": (p.identifiers.get("arxiv", {}).get("published", "") or "")[:4],
            "url": p.identifiers.get("arxiv", {}).get("url", ""),
            "repo": p.repositories[0]["url"] if p.repositories else None,
            "abstract": (p.abstract or "")[:300],
            "keywords": p.keywords,
        }
        for p in papers
    ]

    products = [
        DistProduct(filename="papers.json", payload=paper_dicts),
        DistProduct(filename="papers.jsonl", payload=[json.dumps(d, sort_keys=True, ensure_ascii=False) for d in paper_dicts]),
        DistProduct(filename="repositories.json", payload=repo_dicts),
        DistProduct(filename="categories.json", payload=categories),
        DistProduct(filename="modalities.json", payload=modalities),
        DistProduct(filename="methods.json", payload=methods),
        DistProduct(filename="datasets.json", payload=datasets),
        DistProduct(filename="statistics.json", payload=statistics),
        DistProduct(filename="search-index.json", payload=search_index),
    ]

    # Plus an index manifest.
    manifest = {
        "version": index_version,
        "schema_version": schema_version,
        "generated_at": _utcnow_iso(),
        "conference": conference,
        "statistics": statistics,
        "tracks": dict(_count_dict(p.track for p in papers)),
        "categories": categories,
        "modalities": modalities,
        "methods": methods,
        "datasets": datasets,
        "repository_hosts": dict(_count_dict(r["host"] for p in papers for r in p.repositories)),
    }
    products.append(DistProduct(filename="index.json", payload=manifest))

    return products


def _utcnow_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def write_dist_products(products: Sequence[DistProduct], dist_dir: str) -> int:
    """Write each ``DistProduct`` to ``dist_dir``. Returns file count."""
    target = Path(dist_dir)
    target.mkdir(parents=True, exist_ok=True)
    written = 0
    for product in products:
        path = target / product.filename
        if product.filename.endswith(".jsonl"):
            with open(path, "w", encoding="utf-8") as f:
                for line in product.payload:
                    f.write(line + "\n")
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    product.payload,
                    f,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
        written += 1
    return written
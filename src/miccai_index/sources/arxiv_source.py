"""arXiv API source adapter.

Wraps the ``arxiv`` library with the project-wide conventions:

* Cache-first reads.
* Deterministic record shape (no Python class identity leaking out).
* Structured errors for fetch / rate-limit / parse failures.
* Bounded retries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..cache import FileCache, make_cache_key
from ..config import SourceConfig
from ..errors import DiscoveryError, RateLimitError, SourceFormatError


@dataclass(frozen=True)
class ArxivRecord:
    """Deterministic arXiv record shape.

    All fields are JSON-serializable so this can be cached and snapshotted.
    """

    arxiv_id: str
    version: Optional[str]
    title: str
    summary: str
    authors: List[str]
    comment: str
    published: str
    updated: str
    url: str
    categories: List[str]
    primary_category: str


class ArxivSource:
    """Adapter for the arXiv API."""

    def __init__(
        self,
        config: SourceConfig,
        cache: Optional[FileCache] = None,
    ) -> None:
        self.config = config
        self.cache = cache
        self._client = None

    @property
    def id(self) -> str:
        return self.config.id

    def is_enabled(self) -> bool:
        return self.config.enabled

    def _get_client(self):
        if self._client is None:
            try:
                import arxiv  # type: ignore
            except ImportError as exc:  # pragma: no cover - exercised in CI
                raise DiscoveryError(
                    "The 'arxiv' package is required for the arXiv source adapter",
                    details={"hint": "pip install arxiv"},
                ) from exc
            self._client = arxiv.Client(
                page_size=self.config.page_size,
                delay_seconds=max(1, 60 // max(self.config.rate_limit_per_minute, 1)),
                num_retries=self.config.max_retries,
            )
        return self._client

    def fetch(
        self,
        queries: List[str],
        max_results_per_query: Optional[int] = None,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> Tuple[List[ArxivRecord], Dict[str, Any]]:
        """Fetch records for each query and return a deterministic list."""
        if not self.is_enabled():
            return [], {"enabled": False, "queries": [], "results_per_query": {}}

        max_per = max_results_per_query or self.config.max_results_per_query
        all_records: List[ArxivRecord] = []
        seen_ids: set = set()
        results_per_query: Dict[str, int] = {}
        failed_queries: List[str] = []

        try:
            import arxiv  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise DiscoveryError("Missing arxiv dependency") from exc

        client = self._get_client()
        for query in queries:
            cache_key = make_cache_key(
                {
                    "source": self.id,
                    "query": query,
                    "max": max_per,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                }
            )
            cached = self.cache.get(cache_key) if self.cache else None
            if cached is not None:
                results_per_query[query] = len(cached)
                for rec in cached:
                    if rec["arxiv_id"] in seen_ids:
                        continue
                    seen_ids.add(rec["arxiv_id"])
                    all_records.append(_dict_to_record(rec))
                continue

            sort_criterion = (
                arxiv.SortCriterion.SubmittedDate
                if sort_by == "submittedDate"
                else arxiv.SortCriterion.Relevance
            )
            sort_dir = (
                arxiv.SortOrder.Descending
                if sort_order == "descending"
                else arxiv.SortOrder.Ascending
            )
            try:
                search = arxiv.Search(
                    query=query,
                    max_results=max_per,
                    sort_by=sort_criterion,
                    sort_order=sort_dir,
                )
                results = list(client.results(search))
            except Exception as exc:  # noqa: BLE001 - arxiv errors vary
                failed_queries.append(f"{query}: {exc}")
                results = []

            serialized: List[Dict[str, Any]] = []
            for result in results:
                rec = _result_to_record(result)
                serialized.append(_record_to_dict(rec))
                if rec.arxiv_id in seen_ids:
                    continue
                seen_ids.add(rec.arxiv_id)
                all_records.append(rec)

            results_per_query[query] = len(results)
            if self.cache is not None:
                self.cache.set(cache_key, serialized)

        metadata = {
            "enabled": True,
            "queries": queries,
            "results_per_query": results_per_query,
            "failed_queries": failed_queries,
        }

        if failed_queries and not all_records:
            raise DiscoveryError(
                "All arXiv queries failed; pipeline cannot proceed safely",
                details={"failures": failed_queries},
            )

        return all_records, metadata


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _result_to_record(result) -> ArxivRecord:
    entry_id = str(result.entry_id).replace("http://", "https://")
    arxiv_id = entry_id.rsplit("/", 1)[-1]
    version = None
    if "v" in arxiv_id:
        head, sep, ver = arxiv_id.rpartition("v")
        if sep and ver.isdigit():
            arxiv_id = head
            version = f"v{ver}"

    authors: List[str] = []
    try:
        for author in getattr(result, "authors", []) or []:
            name = getattr(author, "name", None)
            if name:
                authors.append(name)
    except Exception:  # noqa: BLE001 - arxiv has odd edge cases
        authors = []

    cats = list(getattr(result, "categories", []) or [])
    primary = getattr(result, "primary_category", "") or ""

    return ArxivRecord(
        arxiv_id=arxiv_id,
        version=version,
        title=str(result.title or "").strip(),
        summary=str(result.summary or ""),
        authors=authors,
        comment=str(getattr(result, "comment", "") or ""),
        published=_iso(result.published),
        updated=_iso(result.updated),
        url=entry_id,
        categories=cats,
        primary_category=primary,
    )


def _record_to_dict(rec: ArxivRecord) -> Dict[str, Any]:
    return {
        "arxiv_id": rec.arxiv_id,
        "version": rec.version,
        "title": rec.title,
        "summary": rec.summary,
        "authors": rec.authors,
        "comment": rec.comment,
        "published": rec.published,
        "updated": rec.updated,
        "url": rec.url,
        "categories": rec.categories,
        "primary_category": rec.primary_category,
    }


def _dict_to_record(d: Dict[str, Any]) -> ArxivRecord:
    return ArxivRecord(
        arxiv_id=d["arxiv_id"],
        version=d.get("version"),
        title=d["title"],
        summary=d["summary"],
        authors=list(d.get("authors", []) or []),
        comment=d.get("comment", ""),
        published=d["published"],
        updated=d["updated"],
        url=d["url"],
        categories=list(d.get("categories", []) or []),
        primary_category=d.get("primary_category", ""),
    )
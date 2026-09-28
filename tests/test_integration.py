"""Integration tests with a mocked arXiv source."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from miccai_index.config import load_all
from miccai_index.discovery import DiscoveryPipeline
from miccai_index.rendering.data_products import build_dist_products, write_dist_products
from miccai_index.rendering.readme import render_readme
from miccai_index.sources import ArxivSource, ArxivRecord


class FakeArxivSource:
    """Deterministic stand-in for the arXiv source adapter."""

    def __init__(self, records: List[ArxivRecord], enabled: bool = True) -> None:
        self._records = records
        self._enabled = enabled
        self.config = _FakeConfig()

    @property
    def id(self) -> str:
        return "arxiv"

    def is_enabled(self) -> bool:
        return self._enabled

    def fetch(
        self, queries: List[str], max_results_per_query=None, sort_by="submittedDate", sort_order="descending"
    ) -> Tuple[List[ArxivRecord], Dict[str, Any]]:
        if not self._enabled:
            return [], {"enabled": False, "results_per_query": {}, "failed_queries": []}
        return list(self._records), {
            "enabled": True,
            "results_per_query": {q: len(self._records) for q in queries},
            "failed_queries": [],
        }


class _FakeConfig:
    page_size = 100
    delay_seconds = 3
    num_retries = 3
    base_url = "http://example.com"
    id = "arxiv"
    enabled = True
    label = "Fake"
    max_results_per_query = 100
    default_queries = ['ti:"MICCAI"']


def _make_record(arxiv_id: str, title: str, summary: str, comment: str = "") -> ArxivRecord:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return ArxivRecord(
        arxiv_id=arxiv_id,
        version="v1",
        title=title,
        summary=summary,
        authors=["Alice", "Bob"],
        comment=comment,
        published=now,
        updated=now,
        url=f"https://arxiv.org/abs/{arxiv_id}",
        categories=["cs.CV"],
        primary_category="cs.CV",
    )


class PipelineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = load_all()

    def _run(self, records):
        source = FakeArxivSource(records)
        pipeline = DiscoveryPipeline(
            conference=self.configs["conference"],
            taxonomy=self.configs["taxonomy"],
            sources=self.configs["sources"],
            validation=self.configs["validation"],
            arxiv_source=source,
            scope_id="miccai-all-years",
        )
        return pipeline.run()

    def test_accepts_miccai_with_code(self):
        records = [
            _make_record(
                "2601.12345",
                "Brain tumor segmentation",
                "We propose a novel segmentation approach using MRI.",
                "Accepted to MICCAI 2026. Code: https://github.com/user/repo",
            )
        ]
        result = self._run(records)
        self.assertEqual(len(result.papers), 1)
        paper = result.papers[0]
        self.assertIn("Segmentation", paper.categories)
        self.assertEqual(paper.repositories[0]["url"], "https://github.com/user/repo")

    def test_rejects_paper_without_code(self):
        records = [
            _make_record(
                "2601.12345",
                "Brain tumor segmentation",
                "We propose a novel segmentation approach.",
                "Accepted to MICCAI 2026.",
            )
        ]
        result = self._run(records)
        self.assertEqual(len(result.papers), 0)
        self.assertEqual(result.stats["filtered_no_code"], 1)

    def test_rejects_non_miccai_paper(self):
        records = [
            _make_record(
                "2601.12345",
                "Random vision paper",
                "Image classification on ImageNet.",
                "Code: https://github.com/user/repo",
            )
        ]
        result = self._run(records)
        self.assertEqual(len(result.papers), 0)

    def test_dedupes_arxiv_versions(self):
        # Two records with the same base arxiv ID should collapse.
        r1 = _make_record("2601.12345", "Paper", "MICCAI 2026 code https://github.com/a/b", "Accepted to MICCAI 2026")
        r2 = _make_record("2601.12345", "Paper", "MICCAI 2026 code https://github.com/a/b", "Accepted to MICCAI 2026")
        result = self._run([r1, r2])
        self.assertEqual(len(result.papers), 1)
        self.assertEqual(result.stats["duplicates_removed"], 1)

    def test_pipeline_produces_valid_paper_records(self):
        records = [
            _make_record(
                "2601.12345",
                "MRI segmentation",
                "We use MRI scans and propose a segmentation U-Net.",
                "Accepted to MICCAI 2026. Code: https://github.com/user/repo",
            )
        ]
        result = self._run(records)
        paper = result.papers[0]
        self.assertTrue(paper.id.startswith("arxiv:"))
        self.assertIn("MRI", paper.modalities)
        self.assertGreater(len(paper.repositories), 0)
        self.assertGreater(paper.confidence["overall"], 0)


class DataProductsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = load_all()

    def test_build_dist_products_round_trips(self):
        records = [
            _make_record(
                "2601.12345",
                "MRI segmentation",
                "We use MRI scans.",
                "Accepted to MICCAI 2026. Code: https://github.com/user/repo",
            )
        ]
        source = FakeArxivSource(records)
        pipeline = DiscoveryPipeline(
            conference=self.configs["conference"],
            taxonomy=self.configs["taxonomy"],
            sources=self.configs["sources"],
            validation=self.configs["validation"],
            arxiv_source=source,
            scope_id="miccai-all-years",
        )
        result = pipeline.run()
        products = build_dist_products(
            papers=result.papers,
            repositories=result.repositories,
            stats=result.stats,
            conference={"name": "MICCAI", "year": 2026},
            schema_version="1.0.0",
            index_version="0.2.0",
        )
        with tempfile.TemporaryDirectory() as tmp:
            n = write_dist_products(products, tmp)
            self.assertGreater(n, 0)
            # Verify every declared file exists and is valid JSON.
            from miccai_index.rendering.data_products import DIST_FILES
            for fname in DIST_FILES:
                path = Path(tmp) / fname
                self.assertTrue(path.exists(), f"missing {fname}")
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(payload, (dict, list))


if __name__ == "__main__":
    unittest.main()
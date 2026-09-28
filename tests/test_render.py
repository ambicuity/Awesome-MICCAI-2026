"""Tests for the rendering layer."""

from __future__ import annotations

import unittest

from miccai_index.rendering.readme import (
    README_CATEGORY_ORDER,
    build_coverage_report,
    generate_category_markdown,
    render_readme,
    replace_marker_block,
)
from miccai_index.discovery import PaperRecord


def _make_paper(title, arxiv_id, categories, published):
    return PaperRecord(
        id=f"arxiv:{arxiv_id}",
        title=title,
        abstract="",
        authors=[],
        identifiers={
            "arxiv": {
                "id": arxiv_id,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "published": published,
                "updated": published,
            }
        },
        venue={"name": "MICCAI", "year": 2026, "track": "main"},
        track="main",
        categories=categories,
        modalities=[],
        methods=[],
        datasets=[],
        repositories=[
            {
                "id": "github:user/repo",
                "url": "https://github.com/user/repo",
                "host": "github.com",
                "owner": "user",
                "name": "repo",
                "relationship": "official_implementation",
                "confidence": "high",
                "evidence": ["link_found_in_arxiv_comment"],
            }
        ],
        conference_evidence=[],
        confidence={"overall": 0.9, "tasks": {"segmentation": 0.9}},
        provenance={"sources": ["arxiv"]},
        quality={"metadata_completeness": 0.9},
        timestamps={
            "created_at": published,
            "updated_at": published,
        },
        keywords=[],
        note=None,
    )


class RenderTests(unittest.TestCase):
    def test_marker_block_replacement(self):
        text = "before\n<!-- BEGIN SEGMENTATION_PAPERS -->\nold\n<!-- END SEGMENTATION_PAPERS -->\nafter"
        out = replace_marker_block(text, "SEGMENTATION", "* new")
        self.assertIn("* new", out)
        self.assertNotIn("old", out)

    def test_marker_block_missing_raises(self):
        text = "no markers here"
        with self.assertRaises(ValueError):
            replace_marker_block(text, "SEGMENTATION", "x")

    def test_category_markdown_orders_by_date(self):
        p1 = _make_paper("Older Paper", "2601.00001", ["Segmentation"], "2026-01-01T00:00:00+00:00")
        p2 = _make_paper("Newer Paper", "2601.00002", ["Segmentation"], "2026-02-01T00:00:00+00:00")
        body = generate_category_markdown([p1, p2], "Segmentation")
        # Newer first.
        self.assertLess(body.find("Newer"), body.find("Older"))

    def test_confidence_label_in_body(self):
        p = _make_paper("Paper", "2601.00001", ["Segmentation"], "2026-01-01T00:00:00+00:00")
        body = generate_category_markdown([p], "Segmentation")
        self.assertIn("(confidence:", body)

    def test_coverage_report_lists_all_categories(self):
        papers = []
        stats = {"fetched_records": 10, "unique_records": 5, "filtered_non_target": 1, "filtered_track": 0, "filtered_no_code": 0, "uncertain_records": 0}
        report = build_coverage_report(papers, stats, "miccai-2026", "broad", "all")
        for category in README_CATEGORY_ORDER:
            self.assertIn(category, report)

    def test_render_readme_applies_markers(self):
        p = _make_paper("Test Paper", "2601.00001", ["Segmentation"], "2026-01-01T00:00:00+00:00")
        template = """
**Conference Scope**: miccai-2026
**Discovery Mode**: broad
**Last Updated**: old
<!-- BEGIN COVERAGE_REPORT -->
old
<!-- END COVERAGE_REPORT -->
<!-- BEGIN SEGMENTATION_PAPERS -->
old
<!-- END SEGMENTATION_PAPERS -->
<!-- BEGIN RECONSTRUCTION_PAPERS -->
<!-- END RECONSTRUCTION_PAPERS -->
<!-- BEGIN CLASSIFICATION_PAPERS -->
<!-- END CLASSIFICATION_PAPERS -->
<!-- BEGIN IMAGE_REGISTRATION_PAPERS -->
<!-- END IMAGE_REGISTRATION_PAPERS -->
<!-- BEGIN DOMAIN_ADAPTATION_PAPERS -->
<!-- END DOMAIN_ADAPTATION_PAPERS -->
<!-- BEGIN GENERATIVE_MODELS_PAPERS -->
<!-- END GENERATIVE_MODELS_PAPERS -->
<!-- BEGIN GENERAL_PAPERS -->
<!-- END GENERAL_PAPERS -->
""".strip()
        out = render_readme([p], {}, "miccai-2026", "broad", "all", template, timestamp="2026-02-01")
        self.assertIn("Test Paper", out)
        self.assertIn("Conference scope: `miccai-2026`", out)
        self.assertIn("Last Updated**: 2026-02-01", out)


if __name__ == "__main__":
    unittest.main()
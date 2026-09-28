"""Tests for schema and referential validation."""

from __future__ import annotations

import unittest
from pathlib import Path

from miccai_index.config import load_all
from miccai_index.validation import (
    load_schema,
    referential_integrity_check,
    validate_against_schema,
    validate_paper_batch,
)


ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paper_schema = load_schema(str(ROOT / "schemas" / "paper.schema.json"))
        cls.repo_schema = load_schema(str(ROOT / "schemas" / "repository.schema.json"))
        cls.index_schema = load_schema(str(ROOT / "schemas" / "index.schema.json"))

    def _paper_dict(self, **overrides):
        base = {
            "id": "arxiv:2608.12345",
            "title": "A Paper",
            "abstract": "Abstract text",
            "identifiers": {
                "arxiv": {
                    "id": "2608.12345",
                    "version": "v1",
                    "url": "https://arxiv.org/abs/2608.12345",
                    "published": "2026-01-01T00:00:00+00:00",
                    "updated": "2026-01-01T00:00:00+00:00",
                }
            },
            "venue": {"name": "MICCAI", "year": 2026, "track": "main"},
            "track": "main",
            "categories": ["General"],
            "repositories": [
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
            "conference_evidence": [
                {
                    "source": "arxiv_comment",
                    "match": "MICCAI 2026",
                    "strength": "EXPLICIT_STRONG",
                }
            ],
            "confidence": {"overall": 0.9},
            "provenance": {"sources": ["arxiv"]},
            "quality": {"metadata_completeness": 0.8},
            "timestamps": {
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        }
        base.update(overrides)
        return base

    def test_valid_paper(self):
        errors = validate_against_schema(self._paper_dict(), self.paper_schema)
        self.assertEqual(errors, [])

    def test_missing_required_field(self):
        paper = self._paper_dict()
        del paper["title"]
        errors = validate_against_schema(paper, self.paper_schema)
        self.assertTrue(any("title" in e for e in errors))

    def test_bad_arxiv_id_pattern(self):
        paper = self._paper_dict()
        paper["identifiers"]["arxiv"]["id"] = "abc"
        errors = validate_against_schema(paper, self.paper_schema)
        self.assertTrue(any("pattern" in e for e in errors))

    def test_invalid_repository_url(self):
        paper = self._paper_dict()
        paper["repositories"][0]["url"] = "not-a-url"
        errors = validate_against_schema(paper, self.paper_schema)
        self.assertTrue(any("uri" in e or "repositories" in e for e in errors))

    def test_unknown_track_value(self):
        paper = self._paper_dict()
        paper["track"] = "made-up-track"
        errors = validate_against_schema(paper, self.paper_schema)
        self.assertTrue(any("enum" in e for e in errors))

    def test_unknown_additional_field_rejected(self):
        paper = self._paper_dict()
        paper["unknown_extra"] = "x"
        errors = validate_against_schema(paper, self.paper_schema)
        self.assertTrue(any("unexpected" in e for e in errors))

    def test_batch_validation(self):
        papers = [self._paper_dict(), self._paper_dict(id="arxiv:2608.67890")]
        errors = validate_paper_batch(papers, self.paper_schema)
        self.assertEqual(errors, [])

    def test_referential_integrity(self):
        papers = [self._paper_dict(), self._paper_dict(id="arxiv:2608.67890", categories=["MadeUpCategory"])]
        errors = referential_integrity_check(papers, known_categories=["General"])
        self.assertTrue(any("MadeUpCategory" in e for e in errors))

    def test_duplicate_id_in_referential(self):
        papers = [self._paper_dict(), self._paper_dict()]
        errors = referential_integrity_check(papers)
        self.assertTrue(any("duplicate" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
"""Tests for the conference evidence detector."""

from __future__ import annotations

import unittest

from miccai_index.config import load_all
from miccai_index.conference_evidence import (
    collect_conference_evidence,
    extract_year_from_arxiv_id,
    is_target_miccai_paper,
    strongest_evidence,
)


class ConferenceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = load_all()

    def test_explicit_strong_match(self):
        ev = collect_conference_evidence(
            "Paper Title",
            "Abstract",
            "Accepted to MICCAI 2026",
            self.configs["conference"],
        )
        strengths = [e.strength for e in ev]
        self.assertIn("EXPLICIT_STRONG", strengths)

    def test_explicit_year_match(self):
        ev = collect_conference_evidence(
            "Paper Title",
            "MICCAI 2024",
            "",
            self.configs["conference"],
        )
        strengths = [e.strength for e in ev]
        self.assertIn("EXPLICIT", strengths)

    def test_inferred_match(self):
        ev = collect_conference_evidence(
            "Paper Title",
            "Presented at MICCAI",
            "",
            self.configs["conference"],
        )
        strengths = [e.strength for e in ev]
        self.assertIn("INFERRED", strengths)

    def test_strongest_picks_highest(self):
        ev = collect_conference_evidence(
            "Paper Title",
            "MICCAI",
            "Accepted to MICCAI 2026",
            self.configs["conference"],
        )
        self.assertEqual(strongest_evidence(ev), "EXPLICIT_STRONG")

    def test_in_scope_for_year_specific(self):
        in_scope, ev = is_target_miccai_paper(
            title="A Method",
            abstract="Method details",
            comment="Accepted to MICCAI 2026",
            arxiv_id="2608.12345",
            config=self.configs["conference"],
            scope_id="miccai-2026",
            arxiv_year=26,
        )
        self.assertTrue(in_scope)

    def test_out_of_scope_for_wrong_year(self):
        in_scope, ev = is_target_miccai_paper(
            title="A Method",
            abstract="Method details",
            comment="Accepted to MICCAI 2024",
            arxiv_id="2408.12345",
            config=self.configs["conference"],
            scope_id="miccai-2026",
            arxiv_year=24,
        )
        self.assertFalse(in_scope)

    def test_in_scope_all_years_for_2024(self):
        in_scope, ev = is_target_miccai_paper(
            title="A Method",
            abstract="MICCAI 2024 paper",
            comment="",
            arxiv_id="2408.12345",
            config=self.configs["conference"],
            scope_id="miccai-all-years",
            arxiv_year=24,
        )
        self.assertTrue(in_scope)

    def test_weak_evidence_for_year_specific_scope(self):
        # A paper that mentions MICCAI 2026 only in passing should still match.
        in_scope, ev = is_target_miccai_paper(
            title="Paper",
            abstract="We discuss MICCAI 2026 in related work",
            comment="",
            arxiv_id="2408.12345",
            config=self.configs["conference"],
            scope_id="miccai-2026",
            arxiv_year=24,
        )
        # Should be in scope because the year-specific MICCAI 2026 mention is found.
        self.assertTrue(in_scope)


if __name__ == "__main__":
    unittest.main()
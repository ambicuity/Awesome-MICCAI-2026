"""Property-based / invariant tests.

These tests assert invariants that should hold across the pipeline:

* Normalization is idempotent.
* Deduplication never increases record count.
* Conference evidence is monotonic with respect to scope strictness.
* Repository identity is stable across URL forms.
"""

from __future__ import annotations

import unittest

from miccai_index.conference_evidence import is_target_miccai_paper
from miccai_index.config import load_all
from miccai_index.normalization import (
    arxiv_versions_match,
    canonicalize_repository_url,
    parse_arxiv_id,
    parse_repository_url,
)


class IdempotencyTests(unittest.TestCase):
    def test_repository_normalization_idempotent(self):
        urls = [
            "https://github.com/User/Repo/tree/main/src",
            "https://github.com/user/repo",
            "https://github.com/User/Repo",
            "https://github.com/user/Repo",
        ]
        for url in urls:
            canonical = canonicalize_repository_url(url)
            self.assertIsNotNone(canonical)
            assert canonical is not None
            again = canonicalize_repository_url(canonical)
            self.assertEqual(canonical, again)

    def test_arxiv_id_normalization_idempotent(self):
        ids = [
            "2608.13223",
            "2608.13223v3",
            "https://arxiv.org/abs/2608.13223v2",
        ]
        for value in ids:
            parsed = parse_arxiv_id(value)
            self.assertIsNotNone(parsed)
            base = parsed[0]
            again = parse_arxiv_id(base)
            self.assertEqual(again, (base, None))


class DeduplicationInvariants(unittest.TestCase):
    def test_arxiv_versions_match_for_same_paper(self):
        self.assertTrue(arxiv_versions_match("2608.13223v1", "2608.13223v3"))
        self.assertFalse(arxiv_versions_match("2608.13223v1", "2608.13224v1"))

    def test_repository_dedup_via_id(self):
        urls = [
            "https://github.com/user/repo",
            "https://github.com/user/repo/tree/main",
            "https://github.com/user/repo/blob/main/README.md",
        ]
        ids = {parse_repository_url(u).id for u in urls}
        self.assertEqual(len(ids), 1)


class ScopeMonotonicityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = load_all()

    def test_strict_scope_more_restrictive(self):
        """All-year scope includes everything the 2026 scope includes."""
        text_explicit_strong = "Accepted to MICCAI 2026"
        text_all_years = "Accepted to MICCAI 2024"

        in_2026, _ = is_target_miccai_paper(
            "title", "abstract", text_explicit_strong,
            "2608.12345", self.configs["conference"],
            scope_id="miccai-2026", arxiv_year=26,
        )
        in_all, _ = is_target_miccai_paper(
            "title", "abstract", text_explicit_strong,
            "2608.12345", self.configs["conference"],
            scope_id="miccai-all-years", arxiv_year=26,
        )
        self.assertTrue(in_2026)
        self.assertTrue(in_all)

        # The strict 2026 scope should reject a 2024 paper while all-years accepts it.
        in_2026, _ = is_target_miccai_paper(
            "title", "abstract", text_all_years,
            "2408.12345", self.configs["conference"],
            scope_id="miccai-2026", arxiv_year=24,
        )
        in_all, _ = is_target_miccai_paper(
            "title", "abstract", text_all_years,
            "2408.12345", self.configs["conference"],
            scope_id="miccai-all-years", arxiv_year=24,
        )
        self.assertFalse(in_2026)
        self.assertTrue(in_all)


class StableSerialization(unittest.TestCase):
    def test_repository_url_canonical_form(self):
        """The canonical form must be exactly ``https://host/owner/name``."""
        for url in (
            "https://github.com/User/Repo",
            "https://github.com/user/repo.git",
            "https://github.com/user/Repo/tree/main",
        ):
            identity = parse_repository_url(url)
            self.assertEqual(
                identity.url, f"https://{identity.host}/{identity.owner}/{identity.name}"
            )


if __name__ == "__main__":
    unittest.main()
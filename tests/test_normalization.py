"""Tests for URL, identifier, and repository normalization."""

from __future__ import annotations

import unittest

from miccai_index.normalization import (
    canonicalize_repository_url,
    extract_repository_links,
    parse_arxiv_id,
    parse_repository_url,
    repository_id_from_url,
)
from miccai_index.normalization.arxiv import (
    arxiv_id_to_url,
    arxiv_versions_match,
)
from miccai_index.conference_evidence import extract_year_from_arxiv_id


class ArxivNormalizationTests(unittest.TestCase):
    def test_modern_id_with_version(self):
        parsed = parse_arxiv_id("2608.13223v3")
        self.assertEqual(parsed, ("2608.13223", "v3"))

    def test_modern_id_without_version(self):
        parsed = parse_arxiv_id("2608.13223")
        self.assertEqual(parsed, ("2608.13223", None))

    def test_url_form(self):
        parsed = parse_arxiv_id("https://arxiv.org/abs/2608.13223v2")
        self.assertEqual(parsed, ("2608.13223", "v2"))

    def test_legacy_id(self):
        parsed = parse_arxiv_id("cs/0601001")
        self.assertEqual(parsed, ("cs/0601001", None))

    def test_invalid_input(self):
        self.assertIsNone(parse_arxiv_id("not-an-arxiv-id"))
        self.assertIsNone(parse_arxiv_id(""))
        self.assertIsNone(parse_arxiv_id(None))

    def test_url_roundtrip(self):
        url = arxiv_id_to_url("2608.13223", version="v3")
        self.assertEqual(url, "https://arxiv.org/abs/2608.13223v3")

    def test_versions_match_ignoring_version(self):
        self.assertTrue(arxiv_versions_match("2608.13223v1", "2608.13223v3"))

    def test_year_extraction(self):
        self.assertEqual(extract_year_from_arxiv_id("2608.13223"), 26)
        self.assertIsNone(extract_year_from_arxiv_id(None))
        self.assertIsNone(extract_year_from_arxiv_id("not-an-id"))


class RepositoryNormalizationTests(unittest.TestCase):
    def test_simple_github(self):
        identity = parse_repository_url("https://github.com/user/repo")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.id, "github:user/repo")
        self.assertEqual(identity.url, "https://github.com/user/repo")
        self.assertEqual(identity.host, "github.com")
        self.assertEqual(identity.owner, "user")
        self.assertEqual(identity.name, "repo")

    def test_strips_tree_branch(self):
        identity = parse_repository_url("https://github.com/user/repo/tree/main/src")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.url, "https://github.com/user/repo")

    def test_strips_blob_branch(self):
        identity = parse_repository_url("https://github.com/user/repo/blob/main/README.md")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.url, "https://github.com/user/repo")

    def test_strips_dot_git(self):
        identity = parse_repository_url("https://github.com/user/repo.git")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.name, "repo")

    def test_lowercases(self):
        identity = parse_repository_url("https://github.com/User/Repo")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.owner, "user")
        self.assertEqual(identity.name, "repo")

    def test_huggingface_id_token(self):
        identity = parse_repository_url("https://huggingface.co/owner/model")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.id, "hf:owner/model")
        self.assertEqual(identity.host, "huggingface.co")

    def test_huggingface_datasets(self):
        identity = parse_repository_url("https://huggingface.co/datasets/owner/dataset")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.id, "hf:owner/dataset")

    def test_unsupported_host(self):
        self.assertIsNone(parse_repository_url("https://example.com/user/repo"))

    def test_strips_trailing_punct(self):
        identity = parse_repository_url("https://github.com/user/repo.")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.name, "repo")

    def test_strips_malformed_concat(self):
        identity = parse_repository_url("https://github.com/user/repo}{https://github.com/other/repo")
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.url, "https://github.com/user/repo")

    def test_idempotent(self):
        url = "https://github.com/User/Repo/tree/main"
        canonical = canonicalize_repository_url(url)
        self.assertEqual(canonicalize_repository_url(canonical), canonical)

    def test_id_from_url(self):
        self.assertEqual(repository_id_from_url("https://gitlab.com/foo/bar"), "gitlab:foo/bar")
        self.assertIsNone(repository_id_from_url("https://example.com/x/y"))

    def test_extract_from_text(self):
        text = "Code: https://github.com/user1/repo1 and also https://github.com/user1/repo1 again"
        identities = extract_repository_links(text)
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0].id, "github:user1/repo1")


if __name__ == "__main__":
    unittest.main()
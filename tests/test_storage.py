"""Tests for the storage layer and changelog."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from miccai_index.changelog import diff_paper_records, read_changelog, write_changelog
from miccai_index.errors import ValidationError
from miccai_index.storage import index_records, read_jsonl, write_jsonl


class StorageTests(unittest.TestCase):
    def test_roundtrip_jsonl(self):
        records = [{"id": "a", "x": 1}, {"id": "b", "x": 2}]
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "data.jsonl")
            n = write_jsonl(records, path)
            self.assertEqual(n, 2)
            loaded = read_jsonl(path)
            self.assertEqual(loaded, records)

    def test_roundtrip_deterministic_key_order(self):
        record = {"b": 2, "a": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "data.jsonl")
            write_jsonl([record], path)
            content = Path(path).read_text(encoding="utf-8")
            # sort_keys=True ensures a deterministic serialization.
            self.assertEqual(content.strip(), '{"a": 1, "b": 2}')

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_jsonl(str(Path(tmp) / "missing.jsonl")), [])

    def test_invalid_jsonl_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.jsonl"
            path.write_text("not-json\n", encoding="utf-8")
            with self.assertRaises(ValidationError):
                read_jsonl(str(path))

    def test_index_records_dedupes(self):
        records = [{"id": "a"}, {"id": "a"}]
        with self.assertRaises(ValidationError):
            index_records(records)


class ChangelogTests(unittest.TestCase):
    def test_detect_added(self):
        events = diff_paper_records({}, {"a": {"id": "a"}})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "paper_added")
        self.assertEqual(events[0].paper_id, "a")

    def test_detect_removed(self):
        events = diff_paper_records({"a": {"id": "a"}}, {})
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "paper_removed")

    def test_detect_updated(self):
        before = {"a": {"id": "a", "categories": ["Segmentation"]}}
        after = {"a": {"id": "a", "categories": ["Reconstruction"]}}
        events = diff_paper_records(before, after)
        # Expect 1 paper_updated + 1 category_changed for added + 1 for removed.
        types = [e.type for e in events]
        self.assertIn("paper_updated", types)
        self.assertIn("category_changed", types)

    def test_changelog_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "changelog.jsonl")
            events = diff_paper_records({}, {"a": {"id": "a"}})
            n = write_changelog(events, path)
            self.assertEqual(n, len(events))
            loaded = read_changelog(path)
            self.assertEqual(len(loaded), len(events))


if __name__ == "__main__":
    unittest.main()
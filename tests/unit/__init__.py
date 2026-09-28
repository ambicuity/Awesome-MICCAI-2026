"""Tests for the YAML subset loader."""

from __future__ import annotations

import unittest

from miccai_index.config_loader import load_yaml, _coerce_scalar, _unescape_double_quoted
from miccai_index.errors import ConfigurationError


class ScalarCoercionTests(unittest.TestCase):
    def test_null(self):
        self.assertIsNone(_coerce_scalar("null"))
        self.assertIsNone(_coerce_scalar("~"))
        self.assertIsNone(_coerce_scalar(""))

    def test_booleans(self):
        self.assertIs(_coerce_scalar("true"), True)
        self.assertIs(_coerce_scalar("false"), False)
        self.assertIs(_coerce_scalar("TRUE"), True)
        self.assertIs(_coerce_scalar("False"), False)

    def test_numbers(self):
        self.assertEqual(_coerce_scalar("42"), 42)
        self.assertEqual(_coerce_scalar("3.14"), 3.14)
        self.assertEqual(_coerce_scalar("-5"), -5)
        self.assertEqual(_coerce_scalar("1e3"), 1000.0)

    def test_strings_unquoted(self):
        self.assertEqual(_coerce_scalar("hello"), "hello")
        self.assertEqual(_coerce_scalar("a-b-c"), "a-b-c")

    def test_strings_double_quoted(self):
        self.assertEqual(_coerce_scalar('"hello"'), "hello")
        self.assertEqual(_unescape_double_quoted(r"\bfoo\b"), "\bfoo\b")
        self.assertEqual(_unescape_double_quoted(r"line1\nline2"), "line1\nline2")

    def test_strings_single_quoted(self):
        self.assertEqual(_coerce_scalar("'hello'"), "hello")
        # Single-quoted strings treat backslashes literally.
        self.assertEqual(_coerce_scalar(r"'\bfoo\b'"), r"\bfoo\b")
        # Empty string.
        self.assertEqual(_coerce_scalar("''"), "")


class YamlLoadTests(unittest.TestCase):
    def test_simple_mapping(self):
        text = """
        name: foo
        version: 1
        enabled: true
        ratio: 0.5
        """.strip()
        out = load_yaml(text)
        self.assertEqual(out["name"], "foo")
        self.assertEqual(out["version"], 1)
        self.assertIs(out["enabled"], True)
        self.assertEqual(out["ratio"], 0.5)

    def test_nested_mapping(self):
        text = """
        outer:
          inner: value
          flag: true
        """
        out = load_yaml(text)
        self.assertEqual(out["outer"]["inner"], "value")
        self.assertIs(out["outer"]["flag"], True)

    def test_sequence_of_scalars(self):
        text = """
        - one
        - two
        - three
        """
        out = load_yaml(text)
        self.assertEqual(out, ["one", "two", "three"])

    def test_sequence_of_mappings(self):
        text = """
        - id: a
          label: A
        - id: b
          label: B
        """
        out = load_yaml(text)
        self.assertEqual(out[0]["id"], "a")
        self.assertEqual(out[0]["label"], "A")
        self.assertEqual(out[1]["id"], "b")

    def test_mapping_with_sequence_value(self):
        text = """
        conference:
          name: MICCAI
          years:
            - 2024
            - 2025
            - 2026
        """
        out = load_yaml(text)
        self.assertEqual(out["conference"]["name"], "MICCAI")
        self.assertEqual(out["conference"]["years"], [2024, 2025, 2026])

    def test_comments_are_ignored(self):
        text = """
        # top-level comment
        key: value  # trailing comment
        """
        out = load_yaml(text)
        self.assertEqual(out["key"], "value")

    def test_double_quoted_escapes(self):
        text = r'pattern: "\bsegmentation\b"'
        out = load_yaml(text)
        self.assertEqual(out["pattern"], "\bsegmentation\b")


if __name__ == "__main__":
    unittest.main()
"""Minimal YAML subset loader.

We intentionally avoid a YAML dependency. Our config files only use a
constrained subset:

* block mappings ``key: value``
* block sequences ``- item`` and ``- key: value`` (with continuations)
* nested mappings via indentation
* scalars: strings (quoted and unquoted), integers, floats, booleans, null
* comments starting with ``#``

This loader is deliberately strict — it raises ``ConfigurationError`` on
anything it does not understand.
"""

from __future__ import annotations

from typing import Any, List, Optional

from .errors import ConfigurationError


def _coerce_scalar(text: str) -> Any:
    stripped = text.strip()
    if stripped == "" or stripped.lower() in {"null", "~"}:
        return None
    lower = stripped.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False

    # Double-quoted strings: process escape sequences.
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) >= 2:
        return _unescape_double_quoted(stripped[1:-1])

    # Single-quoted strings: literal (only '' escape → ').
    if stripped.startswith("'") and stripped.endswith("'") and len(stripped) >= 2:
        inner = stripped[1:-1].replace("''", "'")
        return inner

    try:
        if "." in stripped or "e" in lower or "E" in lower:
            return float(stripped)
        return int(stripped)
    except ValueError:
        pass

    return stripped


def _unescape_double_quoted(text: str) -> str:
    """Process YAML double-quoted-string escape sequences."""
    out: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            mapping = {
                "n": "\n", "t": "\t", "r": "\r", "0": "\0",
                '"': '"', "\\": "\\", "/": "/", "a": "\a", "b": "\b",
                "f": "\f", "v": "\v",
            }
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
            if nxt == "x" and i + 3 < len(text):
                try:
                    out.append(chr(int(text[i + 2:i + 4], 16)))
                    i += 4
                    continue
                except ValueError:
                    pass
            if nxt == "u" and i + 5 < len(text):
                try:
                    out.append(chr(int(text[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
        out.append(ch)
        i += 1
    return "".join(out)


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:idx]
    return line


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _prepare_lines(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        out.append(stripped)
    return out


class _Parser:
    """Line-based YAML subset parser."""

    def __init__(self, lines: List[str]) -> None:
        self.lines = lines
        self.i = 0
        self.n = len(lines)

    def eof(self) -> bool:
        return self.i >= self.n

    def cur_indent(self) -> Optional[int]:
        if self.eof():
            return None
        return _indent_of(self.lines[self.i])

    def parse(self) -> Any:
        if self.eof():
            return None
        return self._parse_block(_indent_of(self.lines[self.i]))

    def _parse_block(self, indent: int) -> Any:
        """Parse a block at ``indent``. Dispatches to mapping or sequence."""
        line = self.lines[self.i]
        content = line[indent:]
        if content.startswith("- ") or content == "-":
            return self._parse_sequence(indent)
        return self._parse_mapping(indent)

    # --- mappings ----------------------------------------------------------

    def _parse_mapping(self, indent: int) -> dict:
        result: dict = {}
        while not self.eof():
            cur_indent = self.cur_indent()
            if cur_indent is None or cur_indent < indent:
                break
            line = self.lines[self.i]
            content = line[indent:]
            if content.startswith("- "):
                break
            if ":" not in content:
                raise ConfigurationError(f"Expected ':' in mapping line: {line!r}")

            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            self.i += 1

            if val == "":
                # Value is on subsequent indented lines.
                if self.eof() or (self.cur_indent() is not None and self.cur_indent() <= indent):
                    result[key] = None
                else:
                    result[key] = self._parse_block(self.cur_indent())
            else:
                result[key] = _coerce_scalar(val)
        return result

    # --- sequences ---------------------------------------------------------

    def _parse_sequence(self, indent: int) -> list:
        result: list = []
        while not self.eof():
            line = self.lines[self.i]
            cur = _indent_of(line)
            if cur < indent:
                break
            if cur > indent:
                # Continuation lines belong to the previous item's mapping;
                # they are handled by the inline path below.
                break
            content = line[indent:]
            if not content.startswith("- "):
                if content == "-":
                    self.i += 1
                    result.append(self._parse_mapping(indent + 2))
                    continue
                break
            self.i += 1
            rest = content[2:].rstrip()
            result.append(self._parse_seq_item(indent, rest))
        return result

    def _parse_seq_item(self, dash_indent: int, first_rest: str) -> Any:
        """Parse one sequence item whose dash was at ``dash_indent``.

        The item's "content indent" is ``dash_indent + 2``.
        """
        item_indent = dash_indent + 2

        # Empty content: read a block at item_indent.
        if first_rest == "":
            return self._parse_block(item_indent)

        # Quoted scalars are always treated as plain strings, never mappings.
        if _is_quoted(first_rest):
            return _coerce_scalar(first_rest)

        # Inline ``key: value`` or ``key:`` (mapping continuation).
        if ":" in first_rest:
            key, _, val = first_rest.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # Value on subsequent indented lines, then continue reading
                # more keys at item_indent.
                item: dict = {}
                if self.eof() or self.cur_indent() is None or self.cur_indent() <= dash_indent:
                    item[key] = None
                else:
                    item[key] = self._parse_block(self.cur_indent())
                # Now consume sibling keys at item_indent.
                item = self._extend_mapping(item, item_indent)
                return item
            # Inline ``- key: value`` — still allow continuation keys.
            item = {key: _coerce_scalar(val)}
            item = self._extend_mapping(item, item_indent)
            return item

        # Plain scalar.
        return _coerce_scalar(first_rest)

    def _extend_mapping(self, item: dict, item_indent: int) -> dict:
        """Continue reading sibling keys at ``item_indent`` into ``item``."""
        while not self.eof():
            cur = self.cur_indent()
            if cur is None or cur < item_indent:
                break
            if cur > item_indent:
                break
            line = self.lines[self.i]
            content = line[item_indent:]
            if content.startswith("- "):
                break
            if ":" not in content:
                raise ConfigurationError(f"Expected ':' in sequence item: {line!r}")
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            self.i += 1
            if val == "":
                if self.eof() or self.cur_indent() is None or self.cur_indent() <= item_indent:
                    item[key] = None
                else:
                    item[key] = self._parse_block(self.cur_indent())
            else:
                item[key] = _coerce_scalar(val)
        return item


def _is_quoted(text: str) -> bool:
    text = text.strip()
    if len(text) < 2:
        return False
    return (text[0] == text[-1]) and text[0] in ('"', "'")


def load_yaml(text: str) -> Any:
    """Parse the constrained YAML subset used by our config files."""
    lines = _prepare_lines(text)
    if not lines:
        return None
    parser = _Parser(lines)
    return parser.parse()


def load_yaml_file(path: str) -> Any:
    """Load a YAML file from disk and return the parsed value."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return load_yaml(text)
"""arXiv ID normalization.

An arXiv ID can appear in several formats:

* Modern: ``2608.13223`` or ``2608.13223v3``
* Legacy: ``cs/0601001`` or ``math.GT/0309136``
* URL form: ``https://arxiv.org/abs/2608.13223v3``

This module canonicalizes all of these to a tuple of ``(base_id, version)``
where ``base_id`` is the canonical identifier and ``version`` is ``None``
or a ``vN`` string.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

ARXIV_MODERN_PATTERN = re.compile(r"^(?P<id>\d{4}\.\d{4,5})(?:(?P<version>v\d+))?$")
ARXIV_LEGACY_PATTERN = re.compile(r"^(?P<id>[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:(?P<version>v\d+))?$", re.IGNORECASE)
ARXIV_URL_PATTERN = re.compile(
    r"^https?://arxiv\.org/(?:abs|pdf)/(?P<id>(?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(?:(?P<version>v\d+))?"
)


def parse_arxiv_id(value: str) -> Optional[Tuple[str, Optional[str]]]:
    """Parse an arXiv identifier.

    Returns a ``(base_id, version)`` tuple where ``base_id`` is the canonical
    paper identifier and ``version`` is ``None`` or a ``vN`` string. Returns
    ``None`` for unparseable inputs.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if text.lower().startswith(("http://", "https://")):
        m = ARXIV_URL_PATTERN.match(text)
        if not m:
            return None
        return m.group("id"), (m.group("version") or None)

    m = ARXIV_MODERN_PATTERN.match(text)
    if m:
        return m.group("id"), (m.group("version") or None)

    m = ARXIV_LEGACY_PATTERN.match(text)
    if m:
        return m.group("id"), (m.group("version") or None)

    return None


def normalize_arxiv_id(value: str) -> Optional[str]:
    """Return the canonical arXiv ID (``base_id``) or ``None``."""
    parsed = parse_arxiv_id(value)
    if parsed is None:
        return None
    return parsed[0]


def arxiv_id_to_url(base_id: str, version: Optional[str] = None, abs_form: bool = True) -> str:
    """Return the canonical arXiv URL for an ID."""
    suffix = "/abs" if abs_form else "/pdf"
    version_suffix = version if version else ""
    return f"https://arxiv.org/abs/{base_id}{version_suffix}" if abs_form else f"https://arxiv.org/pdf/{base_id}{version_suffix}"


def arxiv_versions_match(value_a: str, value_b: str) -> bool:
    """Return True if two arXiv identifiers refer to the same paper (ignoring version)."""
    a = normalize_arxiv_id(value_a)
    b = normalize_arxiv_id(value_b)
    if a is None or b is None:
        return False
    return a == b
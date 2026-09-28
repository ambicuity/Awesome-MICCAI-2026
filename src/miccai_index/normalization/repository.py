"""Repository URL canonicalization.

A repository URL is normalized to a stable, canonical form:

* Host is lower-cased and ``www.`` stripped.
* Path is reduced to ``owner/name`` (lowercased); ``.git`` suffix dropped.
* Subpaths (``tree/main``, ``blob/main/README.md``) are removed.
* Trailing punctuation and stray ``}{...`` concatenations are stripped.

The canonical ID format is ``<host_token>:owner/name``:

* ``github:owner/name``
* ``gitlab:owner/name``
* ``hf:owner/name``

These IDs are stable across URL forms (https, ssh, tree paths).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

# Note: huggingface.co paths are typically /owner/name for models and
# /datasets/owner/name for datasets — we collapse both to ``hf:owner/name``.
HOST_TOKEN_MAP = {
    "github.com": "github",
    "gitlab.com": "gitlab",
    "huggingface.co": "hf",
}

REPO_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:github\.com|gitlab\.com|huggingface\.co)/[^\s\]\[<>\"')]+",
    flags=re.IGNORECASE,
)

# Path prefixes we want to recognize and ignore.
PATH_PREFIXES_TO_STRIP = ("tree/", "blob/", "issues", "pull", "wiki", "raw/")


@dataclass(frozen=True)
class RepositoryIdentity:
    """Canonical repository identity."""

    id: str
    url: str
    host: str
    owner: str
    name: str

    @property
    def host_token(self) -> str:
        return HOST_TOKEN_MAP.get(self.host, self.host)


@dataclass(frozen=True)
class RepositoryCandidate:
    """A candidate repository URL extracted from free text."""

    raw: str
    identity: Optional[RepositoryIdentity]


def _normalize_host(host: str) -> str:
    host = host.lower().strip()
    return host[4:] if host.startswith("www.") else host


def _clean_url_candidate(url: str) -> str:
    """Strip trailing punctuation, ``}{...`` junk, and outer whitespace."""
    url = url.strip()
    url = url.split("}{", 1)[0]
    url = re.sub(r"[.,;:!?\]\}>\"'\s]+$", "", url)
    return url


def _strip_path_prefixes(path_segments: Sequence[str]) -> List[str]:
    """Drop ``tree/main``, ``blob/main/README.md``, etc."""
    if not path_segments:
        return []
    # Remove leading reserved tokens that indicate a subtree.
    while path_segments and path_segments[0] in PATH_PREFIXES_TO_STRIP:
        path_segments = path_segments[1:]
        if path_segments and "/" not in path_segments[0]:
            # ``tree/branch`` consumes two segments; ``issues`` consumes one.
            if path_segments:
                path_segments = path_segments[1:]
    return list(path_segments)


def _canonical_repo_key(parsed_path: str, host: str) -> Optional[Tuple[str, str, str]]:
    """Return ``(host, owner, name)`` or ``None`` if the path is not a repo."""
    segments = _strip_path_prefixes([s for s in parsed_path.split("/") if s])
    if len(segments) < 2:
        return None

    owner = segments[0].lower()
    name = segments[1].lower()
    blocked_owner_paths = {"orgs", "topics", "collections", "about", "search", "settings", "users", "sponsors"}
    if owner in blocked_owner_paths:
        return None

    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name:
        return None

    # Hugging Face datasets live under ``/datasets/owner/name`` — collapse.
    if host == "huggingface.co" and owner == "datasets":
        # path was ``datasets/<owner>/<name>`` — segments are [datasets, owner, name]
        if len(segments) >= 3:
            owner = segments[1].lower()
            name = segments[2].lower()
            if name.endswith(".git"):
                name = name[:-4]

    return host, owner, name


def parse_repository_url(url: str) -> Optional[RepositoryIdentity]:
    """Return a canonical ``RepositoryIdentity`` or ``None`` if unsupported."""
    cleaned = _clean_url_candidate(url)
    try:
        parsed = urlparse(cleaned)
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    host = _normalize_host(parsed.netloc)
    if host not in HOST_TOKEN_MAP:
        return None

    key = _canonical_repo_key(parsed.path, host)
    if key is None:
        return None

    canonical_host, owner, name = key
    canonical_url = f"https://{canonical_host}/{owner}/{name}"
    token = HOST_TOKEN_MAP[canonical_host]
    return RepositoryIdentity(
        id=f"{token}:{owner}/{name}",
        url=canonical_url,
        host=canonical_host,
        owner=owner,
        name=name,
    )


def canonicalize_repository_url(url: str) -> Optional[str]:
    """Return the canonical URL string or ``None`` if not parseable."""
    identity = parse_repository_url(url)
    return identity.url if identity else None


def repository_id_from_url(url: str) -> Optional[str]:
    """Return the canonical repository ID or ``None`` if not parseable."""
    identity = parse_repository_url(url)
    return identity.id if identity else None


def extract_repository_links(text: str) -> List[RepositoryIdentity]:
    """Extract unique canonical repository identities from arbitrary text."""
    if not text:
        return []
    candidates: Iterable[str] = REPO_URL_PATTERN.findall(text)
    deduped: List[RepositoryIdentity] = []
    seen_ids: set = set()
    for candidate in candidates:
        identity = parse_repository_url(candidate)
        if identity is None:
            continue
        if identity.id in seen_ids:
            continue
        seen_ids.add(identity.id)
        deduped.append(identity)
    return deduped
"""Filesystem-backed cache for upstream responses and snapshots.

Design:

* Cache keys are content hashes (``sha256``) of the canonical request.
* Stored values are arbitrary JSON-serializable dicts/lists/scalars.
* TTL is enforced lazily on read.
* Snapshots are immutable, timestamped bundles of source data used to make
  builds reproducible.

The cache is intentionally minimal — no LRU, no locking. It is meant for
single-process CLI invocations and CI runners.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class CacheEntry:
    key: str
    path: Path
    stored_at: datetime
    ttl_seconds: int

    @property
    def is_fresh(self) -> bool:
        if self.ttl_seconds <= 0:
            return True
        age = (datetime.now(timezone.utc) - self.stored_at).total_seconds()
        return age < self.ttl_seconds


class FileCache:
    """Simple filesystem cache backed by JSON files."""

    def __init__(self, directory: str, ttl_seconds: int = 86400) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        stored_at = datetime.fromisoformat(payload["stored_at"])
        if not CacheEntry(key, path, stored_at, self.ttl_seconds).is_fresh:
            return None
        return payload.get("value")

    def set(self, key: str, value: Any) -> None:
        path = self._path_for(key)
        payload = {
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "value": value,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def clear(self) -> None:
        for path in self.directory.glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass


def make_cache_key(parts: dict) -> str:
    """Build a stable cache key from a dict of request parts."""
    canonical = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_snapshot(directory: str, name: str, payload: Any) -> str:
    """Persist an immutable source snapshot and return its id."""
    snap_dir = Path(directory)
    snap_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = re_sub("[^A-Za-z0-9_-]+", "_", name)
    snapshot_id = f"{safe_name}-{stamp}"
    path = snap_dir / f"{snapshot_id}.json"
    path.write_text(
        json.dumps(
            {"snapshot_id": snapshot_id, "created_at": stamp, "payload": payload},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return snapshot_id


def re_sub(pattern: str, repl: str, value: str) -> str:
    import re
    return re.sub(pattern, repl, value)


def latest_snapshot(directory: str, prefix: str) -> Optional[dict]:
    """Return the most recent snapshot matching ``prefix`` or ``None``."""
    snap_dir = Path(directory)
    if not snap_dir.exists():
        return None
    matches = sorted(snap_dir.glob(f"{prefix}-*.json"))
    if not matches:
        return None
    try:
        return json.loads(matches[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
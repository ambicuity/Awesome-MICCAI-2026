"""Change tracking between pipeline runs.

The changelog records structural diffs:

* ``paper_added``
* ``paper_removed``
* ``paper_updated``
* ``category_changed``
* ``repository_added``
* ``repository_removed``

Diffing is deterministic and based on canonical identifiers and a sorted JSON
representation of each record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChangeEvent:
    type: str
    paper_id: Optional[str] = None
    repository_id: Optional[str] = None
    field_name: Optional[str] = None
    before: Any = None
    after: Any = None
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        # Field with default factory can't have any required fields after it;
        # this guard is purely defensive.
        return

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"type": self.type, "date": self.date}
        if self.paper_id is not None:
            out["paper_id"] = self.paper_id
        if self.repository_id is not None:
            out["repository_id"] = self.repository_id
        if self.field_name is not None:
            out["field"] = self.field_name
        if self.before is not None:
            out["before"] = self.before
        if self.after is not None:
            out["after"] = self.after
        return out


def diff_paper_records(previous: Dict[str, dict], current: Dict[str, dict]) -> List[ChangeEvent]:
    events: List[ChangeEvent] = []
    prev_ids = set(previous)
    cur_ids = set(current)

    for pid in sorted(cur_ids - prev_ids):
        events.append(ChangeEvent(type="paper_added", paper_id=pid))

    for pid in sorted(prev_ids - cur_ids):
        events.append(ChangeEvent(type="paper_removed", paper_id=pid))

    for pid in sorted(cur_ids & prev_ids):
        before = previous[pid]
        after = current[pid]
        if before == after:
            continue
        events.append(ChangeEvent(type="paper_updated", paper_id=pid))
        before_cats = set(before.get("categories", []) or [])
        after_cats = set(after.get("categories", []) or [])
        added = sorted(after_cats - before_cats)
        removed = sorted(before_cats - after_cats)
        for cat in added:
            events.append(
                ChangeEvent(
                    type="category_changed",
                    paper_id=pid,
                    field_name="category_added",
                    after=cat,
                )
            )
        for cat in removed:
            events.append(
                ChangeEvent(
                    type="category_changed",
                    paper_id=pid,
                    field_name="category_removed",
                    before=cat,
                )
            )
        before_repos = {r.get("id") for r in before.get("repositories", []) if r.get("id")}
        after_repos = {r.get("id") for r in after.get("repositories", []) if r.get("id")}
        for rid in sorted(after_repos - before_repos):
            events.append(ChangeEvent(type="repository_added", paper_id=pid, repository_id=rid))
        for rid in sorted(before_repos - after_repos):
            events.append(ChangeEvent(type="repository_removed", paper_id=pid, repository_id=rid))

    return events


def write_changelog(events: List[ChangeEvent], path: str) -> int:
    """Append change events to ``path`` as JSONL."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(p, "a", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def read_changelog(path: str) -> List[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out: List[dict] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out
"""JSONL-backed storage for canonical paper and repository records.

Storage layout:

```
data/
  papers.jsonl          # canonical paper records
  repositories.jsonl    # canonical repository records
  snapshots/            # immutable source snapshots
```

All records are sorted deterministically when written. Reads return the same
records in the same order across runs given the same input.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .errors import ValidationError


def write_jsonl(records: Iterable[dict], path: str) -> int:
    """Write ``records`` to ``path`` as JSONL. Returns the number written."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(p, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def read_jsonl(path: str) -> List[dict]:
    """Read JSONL records from ``path``. Returns ``[]`` if missing."""
    p = Path(path)
    if not p.exists():
        return []
    out: List[dict] = []
    with open(p, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"Invalid JSONL at {path}:{line_no}: {exc.msg}"
                )
    return out


def iter_jsonl(path: str) -> Iterator[dict]:
    yield from read_jsonl(path)


def index_records(records: Iterable[dict], key: str = "id") -> Dict[str, dict]:
    """Build a ``{id: record}`` index, raising on duplicate keys."""
    out: Dict[str, dict] = {}
    for record in records:
        rid = record.get(key)
        if not rid:
            raise ValidationError(f"Record missing '{key}'")
        if rid in out:
            raise ValidationError(f"Duplicate {key}: {rid}")
        out[rid] = record
    return out


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def default_data_paths(repo_root: Optional[Path] = None) -> Dict[str, str]:
    root = (repo_root or Path.cwd()).resolve()
    return {
        "papers": str(root / "data" / "papers.jsonl"),
        "repositories": str(root / "data" / "repositories.jsonl"),
        "snapshots": str(root / "data" / "snapshots"),
        "dist": str(root / "dist"),
        "schemas": str(root / "schemas"),
    }
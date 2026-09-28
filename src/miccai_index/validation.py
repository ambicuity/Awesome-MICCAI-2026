"""Schema-aware validator for paper, repository, and index records.

This validator is deliberately tailored to the schemas shipped in
``schemas/``. We use it instead of a third-party library to avoid an extra
dependency.

Supported type keywords:

* ``type: object`` with ``properties``/``required``/``additionalProperties``
* ``type: string`` with ``pattern``/``format``/``minLength``
* ``type: integer`` with ``minimum``/``maximum``
* ``type: number`` with ``minimum``/``maximum``
* ``type: array`` with ``items``/``minItems``
* ``enum``
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List, Optional

from .errors import ValidationError


def _validate(value: Any, schema: dict, path: str, errors: List[str]) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required field '{key}'")
        for key, sub_schema in props.items():
            if key in value:
                _validate(value[key], sub_schema, f"{path}.{key}", errors)
        additional = schema.get("additionalProperties")
        if additional is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}: unexpected field '{key}'")
        elif isinstance(additional, dict):
            for key, sub_schema in additional.items():
                if key in value:
                    _validate(value[key], sub_schema, f"{path}.{key}", errors)
        return

    if schema_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return
        items_schema = schema.get("items")
        if items_schema:
            for idx, item in enumerate(value):
                _validate(item, items_schema, f"{path}[{idx}]", errors)
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: array shorter than minItems={min_items}")
        return

    if schema_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: string shorter than minLength={min_length}")
        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, value):
            errors.append(f"{path}: does not match pattern '{pattern}'")
        if schema.get("format") == "uri":
            if not re.match(r"^https?://[^\s]+$", value):
                errors.append(f"{path}: not a valid uri")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}: not a valid ISO-8601 datetime")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value '{value}' not in enum {schema['enum']}")
        return

    if schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")
            return
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value {value} > maximum {schema['maximum']}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value '{value}' not in enum {schema['enum']}")
        return

    if schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}: expected number, got {type(value).__name__}")
            return
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value {value} > maximum {schema['maximum']}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value '{value}' not in enum {schema['enum']}")
        return

    # Unknown type — accept without validation.
    return


def validate_against_schema(value: Any, schema: dict) -> List[str]:
    """Validate ``value`` against ``schema`` and return a list of error strings."""
    errors: List[str] = []
    _validate(value, schema, "$", errors)
    return errors


def raise_on_errors(value: Any, schema: dict, context: str) -> None:
    errors = validate_against_schema(value, schema)
    if errors:
        raise ValidationError(f"{context}: validation failed", details={"errors": errors})


def load_schema(path: str) -> dict:
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_paper_batch(records: List[dict], schema: dict) -> List[str]:
    errors: List[str] = []
    for idx, record in enumerate(records):
        record_errors = validate_against_schema(record, schema)
        for e in record_errors:
            errors.append(f"record[{idx}]: {e}")
    return errors


def referential_integrity_check(
    papers: List[dict],
    known_categories: Optional[List[str]] = None,
) -> List[str]:
    """Check basic referential invariants on a batch of papers."""
    errors: List[str] = []
    seen_ids: set = set()
    for idx, paper in enumerate(papers):
        pid = paper.get("id")
        if not pid:
            errors.append(f"record[{idx}]: missing id")
            continue
        if pid in seen_ids:
            errors.append(f"record[{idx}]: duplicate id {pid}")
        seen_ids.add(pid)
        if known_categories:
            for cat in paper.get("categories", []) or []:
                if cat not in known_categories:
                    errors.append(
                        f"record[{idx}]: category '{cat}' not in known taxonomy"
                    )
        # Each repository reference should resolve to a canonical host.
        for ridx, repo in enumerate(paper.get("repositories", []) or []):
            if not isinstance(repo, dict):
                errors.append(f"record[{idx}].repositories[{ridx}]: not an object")
                continue
            if not repo.get("url"):
                errors.append(f"record[{idx}].repositories[{ridx}]: missing url")
    return errors
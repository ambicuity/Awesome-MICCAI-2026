"""Structured error taxonomy for the MICCAI index pipeline.

All errors carry a stable ``code`` for programmatic handling and a human-readable
``message``. Subclasses add context fields that help automation surface
actionable information in CI summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class IndexError_(Exception):
    """Base error for the MICCAI index pipeline."""

    message: str
    code: str = "index_error"
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.details:
            return f"[{self.code}] {self.message} ({self.details})"
        return f"[{self.code}] {self.message}"


class ConfigurationError(IndexError_):
    """Raised when configuration is missing, invalid, or inconsistent."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message=message, code="configuration_error", details=details or {})


class DiscoveryError(IndexError_):
    """Raised by source adapters for fetch / parse failures."""


class RateLimitError(DiscoveryError):
    """Raised when an upstream source returns a rate-limit response."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        merged = dict(details or {})
        if retry_after is not None:
            merged["retry_after"] = retry_after
        super().__init__(message=message, code="rate_limit_error", details=merged)


class SourceFormatError(DiscoveryError):
    """Raised when an upstream response cannot be parsed."""


class NormalizationError(IndexError_):
    """Raised when normalization cannot produce a canonical value."""


class ValidationError(IndexError_):
    """Raised when validation rejects an input."""


class RepositoryResolutionError(IndexError_):
    """Raised when a repository URL cannot be resolved."""


class GenerationError(IndexError_):
    """Raised when rendering / generation cannot complete successfully."""
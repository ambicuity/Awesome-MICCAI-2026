"""Health checks for daily update runs.

Implements the configured health thresholds so a degraded discovery does not
silently overwrite the canonical dataset. See ``config/validation.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import ValidationConfig


@dataclass
class HealthReport:
    healthy: bool
    coverage_ratio: float
    category_drift_ratio: float
    repository_loss_ratio: float
    issues: List[str]


def evaluate_run_health(
    *,
    previous_paper_count: int,
    current_paper_count: int,
    previous_categories: Dict[str, int],
    current_categories: Dict[str, int],
    previous_repo_hosts: Dict[str, int],
    current_repo_hosts: Dict[str, int],
    config: ValidationConfig,
) -> HealthReport:
    """Evaluate whether the current run meets the health thresholds."""
    issues: List[str] = []

    if previous_paper_count > 0:
        coverage_ratio = current_paper_count / previous_paper_count
    else:
        coverage_ratio = 1.0 if current_paper_count > 0 else 0.0

    min_cov = config.health.minimum_coverage_ratio
    if coverage_ratio < min_cov:
        issues.append(
            f"coverage_ratio={coverage_ratio:.3f} < minimum {min_cov:.3f} "
            f"(previous={previous_paper_count}, current={current_paper_count})"
        )

    # Category drift: how many categories changed by more than 30% in either
    # direction, divided by total categories.
    drift_count = 0
    all_categories = set(previous_categories) | set(current_categories)
    for cat in all_categories:
        prev = previous_categories.get(cat, 0)
        curr = current_categories.get(cat, 0)
        if prev == 0 and curr == 0:
            continue
        denom = max(prev, 1)
        change = abs(curr - prev) / denom
        if change > 0.3:
            drift_count += 1
    category_drift_ratio = drift_count / max(len(all_categories), 1)
    max_drift = config.health.max_category_drift_ratio
    if category_drift_ratio > max_drift:
        issues.append(
            f"category_drift_ratio={category_drift_ratio:.3f} > max {max_drift:.3f}"
        )

    # Repository host loss: how many repository hosts disappeared.
    prev_hosts = sum(previous_repo_hosts.values())
    curr_hosts = sum(current_repo_hosts.values())
    if prev_hosts > 0:
        loss_ratio = max(0.0, (prev_hosts - curr_hosts) / prev_hosts)
    else:
        loss_ratio = 0.0
    max_loss = config.health.max_repository_loss_ratio
    if loss_ratio > max_loss:
        issues.append(
            f"repository_loss_ratio={loss_ratio:.3f} > max {max_loss:.3f}"
        )

    return HealthReport(
        healthy=not issues,
        coverage_ratio=coverage_ratio,
        category_drift_ratio=category_drift_ratio,
        repository_loss_ratio=loss_ratio,
        issues=issues,
    )
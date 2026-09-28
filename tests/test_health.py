"""Tests for the health-threshold evaluator."""

from __future__ import annotations

import unittest

from miccai_index.config import load_validation_config
from miccai_index.health import evaluate_run_health


class HealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_validation_config("config/validation.yaml")

    def test_healthy_when_counts_match(self):
        report = evaluate_run_health(
            previous_paper_count=100,
            current_paper_count=100,
            previous_categories={"Segmentation": 50, "General": 50},
            current_categories={"Segmentation": 50, "General": 50},
            previous_repo_hosts={"github.com": 100},
            current_repo_hosts={"github.com": 100},
            config=self.config,
        )
        self.assertTrue(report.healthy)
        self.assertEqual(report.coverage_ratio, 1.0)

    def test_unhealthy_when_coverage_drops(self):
        report = evaluate_run_health(
            previous_paper_count=100,
            current_paper_count=20,
            previous_categories={"Segmentation": 50},
            current_categories={"Segmentation": 20},
            previous_repo_hosts={"github.com": 100},
            current_repo_hosts={"github.com": 20},
            config=self.config,
        )
        self.assertFalse(report.healthy)
        self.assertLess(report.coverage_ratio, self.config.health.minimum_coverage_ratio)

    def test_unhealthy_when_repo_loss_too_large(self):
        report = evaluate_run_health(
            previous_paper_count=100,
            current_paper_count=100,
            previous_categories={"Segmentation": 50},
            current_categories={"Segmentation": 50},
            previous_repo_hosts={"github.com": 100},
            current_repo_hosts={"github.com": 30},
            config=self.config,
        )
        self.assertFalse(report.healthy)
        self.assertGreater(
            report.repository_loss_ratio,
            self.config.health.max_repository_loss_ratio,
        )

    def test_unhealthy_when_category_drift(self):
        prev = {"Segmentation": 50, "General": 50}
        curr = {"Segmentation": 100, "General": 0}
        report = evaluate_run_health(
            previous_paper_count=100,
            current_paper_count=100,
            previous_categories=prev,
            current_categories=curr,
            previous_repo_hosts={"github.com": 100},
            current_repo_hosts={"github.com": 100},
            config=self.config,
        )
        self.assertFalse(report.healthy)
        self.assertGreater(report.category_drift_ratio, 0)


if __name__ == "__main__":
    unittest.main()
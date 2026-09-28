"""Tests for the taxonomy classifier."""

from __future__ import annotations

import unittest

from miccai_index.classification import (
    classify_datasets,
    classify_methods,
    classify_modalities,
    classify_tasks,
)
from miccai_index.config import load_all


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = load_all()
        cls.taxonomy = cls.configs["taxonomy"]

    def test_segmentation_in_tasks(self):
        result = classify_tasks(
            title="Brain tumor segmentation",
            abstract="We propose a novel U-Net based segmentation approach.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertIn("segmentation", ids)

    def test_multi_label(self):
        result = classify_tasks(
            title="Diffusion model for brain tumor segmentation and reconstruction",
            abstract="Diffusion-based reconstruction with segmentation prior.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertIn("segmentation", ids)
        self.assertIn("reconstruction", ids)
        self.assertIn("generative_models", ids)

    def test_modality_mri(self):
        result = classify_modalities(
            title="Brain MRI analysis",
            abstract="T1-weighted MRI scans were used.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertIn("mri", ids)

    def test_modality_pathology(self):
        result = classify_modalities(
            title="Histopathology classification",
            abstract="Whole-slide images of H&E stained tissue.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertIn("pathology", ids)

    def test_method_diffusion(self):
        result = classify_methods(
            title="Diffusion-based segmentation",
            abstract="We use a denoising diffusion model.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertIn("diffusion", ids)

    def test_method_transformer(self):
        result = classify_methods(
            title="Swin Transformer for medical imaging",
            abstract="We use a swin transformer backbone.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertIn("transformer", ids)

    def test_dataset_recognition(self):
        ds = classify_datasets(
            title="Brain tumor segmentation on BraTS",
            abstract="Using the BraTS 2024 challenge dataset.",
            taxonomy=self.taxonomy,
        )
        self.assertIn("BraTS", ds)

    def test_no_match_returns_general(self):
        result = classify_tasks(
            title="Completely unrelated",
            abstract="Just talking about math without any medical imaging terms.",
            taxonomy=self.taxonomy,
        )
        ids = [a.label_id for a in result.assignments]
        self.assertEqual(ids, ["general"])
        self.assertTrue(result.unmatched)

    def test_title_hits_count_more(self):
        """Title hits should outweigh abstract hits for the same pattern."""
        result = classify_tasks(
            title="Segmentation for cardiac MRI",
            abstract="Some unrelated context without the keywords we look for.",
            taxonomy=self.taxonomy,
        )
        seg = next((a for a in result.assignments if a.label_id == "segmentation"), None)
        self.assertIsNotNone(seg)
        assert seg is not None
        # Title hit contributes weight*2.
        self.assertGreaterEqual(seg.score, 6)  # at least 3*2 from title "segmentation"

    def test_confidence_in_range(self):
        result = classify_tasks(
            title="Segmentation",
            abstract="segmentation",
            taxonomy=self.taxonomy,
        )
        for assignment in result.assignments:
            self.assertGreaterEqual(assignment.confidence, 0.0)
            self.assertLessEqual(assignment.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
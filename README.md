# Awesome MICCAI 2026

[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)
[![CI](https://github.com/ambicuity/Awesome-MICCAI-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/ambicuity/Awesome-MICCAI-2026/actions/workflows/ci.yml)
[![Data Validation](https://github.com/ambicuity/Awesome-MICCAI-2026/actions/workflows/validate.yml/badge.svg)](https://github.com/ambicuity/Awesome-MICCAI-2026/actions/workflows/validate.yml)
[![Schema](https://img.shields.io/badge/schema-1.0.0-blue.svg)](./schemas/paper.schema.json)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)

> A curated, machine-readable research index of MICCAI papers with public code — built on a deterministic, validated, reproducible pipeline.

This repository is both an **awesome list** and the **canonical dataset** that powers it. The README you are reading is one rendered view of a much richer structured index designed to support search, dashboards, and downstream research tools.

## ✨ What's new (v0.2 — research-infrastructure release)

This is a major rewrite. The list of papers you see below is preserved, but the underlying system is now:

- **Canonical data model** — every paper and repository is validated against a JSON Schema (`schemas/`) before render.
- **Evidence-based conference detection** — papers are tagged with structured conference evidence (`EXPLICIT_STRONG` → `WEAK`) instead of brittle keyword matching.
- **Hierarchical taxonomy** — tasks, modalities, methods, and datasets are classified with multi-label weighted rules and per-label confidence.
- **Machine-readable data products** — `dist/papers.json`, `papers.jsonl`, `repositories.json`, `search-index.json`, `statistics.json` and more are generated alongside the README.
- **Offline / reproducible** — `python -m miccai_index build --offline` validates and renders existing data without any network calls.
- **PR-based automation** — daily runs open a PR instead of force-pushing to `main`.
- **Health-thresholded daily run** — if discovery drops unexpectedly, the last known good artifact is preserved.

📚 See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md), [`docs/DATA_MODEL.md`](./docs/DATA_MODEL.md), and [`docs/TAXONOMY.md`](./docs/TAXONOMY.md) for the full design.

## 📋 Quick Links

- **Machine-readable data**: [`dist/papers.json`](./dist/papers.json) · [`dist/papers.jsonl`](./dist/papers.jsonl) · [`dist/index.json`](./dist/index.json)
- **Search index**: [`dist/search-index.json`](./dist/search-index.json)
- **Statistics**: [`dist/statistics.json`](./dist/statistics.json)
- **All repositories**: [`dist/repositories.json`](./dist/repositories.json)
- **Browse by taxonomy**: [Tasks](#-segmentation) · [Modalities](#modality-browse) · [Methods](#method-browse) · [Tracks](#track-browse)
- **Documentation**: [`ARCHITECTURE`](./docs/ARCHITECTURE.md) · [`DATA_MODEL`](./docs/DATA_MODEL.md) · [`TAXONOMY`](./docs/TAXONOMY.md) · [`DATA_SOURCES`](./docs/DATA_SOURCES.md) · [`AUTOMATION`](./docs/AUTOMATION.md) · [`CONTRIBUTING`](./CONTRIBUTING.md) · [`SECURITY`](./SECURITY.md)

## 🔍 What This Project Is

A reproducible, schema-validated pipeline that:

1. **Discovers** MICCAI papers from arXiv metadata using configurable queries.
2. **Normalizes** paper identifiers (arXiv versions), repository URLs (GitHub/GitLab/HuggingFace → canonical `host:owner/name`), and conference scope.
3. **Classifies** each paper with multi-label weighted evidence across tasks, modalities, methods, and datasets.
4. **Validates** the canonical dataset against JSON Schema and referential invariants before any rendering.
5. **Renders** this README, the `dist/` data products, a changelog, and CI summaries.

The pipeline is **deterministic**: same input snapshot, same configuration, byte-for-byte same output.

The pipeline is **incremental**: a file cache and content-hash keyed snapshots avoid re-fetching and re-processing on every run.

The pipeline is **observable**: every run emits structured stats and a JSONL changelog (`data/changelog.jsonl`) for paper-level diffs.

## 🧰 Quick Start

```bash
git clone https://github.com/ambicuity/Awesome-MICCAI-2026
cd Awesome-MICCAI-2026
make setup      # pip install -r requirements.txt
make test       # 100+ unit, integration, and property tests
make validate   # validate generated data without network
make build      # full pipeline (network required)
make report     # analytics over existing dataset
```

Direct CLI:

```bash
python -m miccai_index --help
python -m miccai_index build --scope miccai-all-years --mode broad --tracks all
python -m miccai_index validate --offline
python -m miccai_index report
```

## ✅ Inclusion Policy

- Source of truth: arXiv metadata (`title`, `abstract`, `comment`) + public repository URLs (GitHub, GitLab, HuggingFace).
- Conference affiliation is established via structured evidence (`EXPLICIT_STRONG`/`EXPLICIT`/`INFERRED`/`WEAK`), not raw keyword matches.
- A paper may appear in multiple categories when it strongly matches multiple tasks.
- Inclusion is **reversible**: removing a paper from the dataset requires an explicit, auditable reason. We never silently drop records.

## 🔐 Trust & Validation

- Content between `<!-- BEGIN … -->` and `<!-- END … -->` markers is generated by the pipeline; everything outside the markers is hand-written prose.
- `python -m miccai_index validate` checks JSON-Schema, referential integrity, URL canonicality, and confidence thresholds.
- CI runs the test suite, schema validation, and a smoke build on every PR.
- The daily automation is **PR-only** — it never force-pushes to `main`.

## 📈 Coverage Report

<!-- BEGIN COVERAGE_REPORT -->
- Conference scope: `miccai-all-years`
- Discovery mode: `broad`
- Tracks: `all`
- Total code-backed papers: `7`
- Fetched arXiv records: `0`
- Unique arXiv records: `0`
- Filtered (non-target): `0`
- Filtered (track): `0`
- Filtered (no code links): `0`
- Uncertain taxonomy papers: `0`

| Category | Count | Gap to 1000 |
|---|---:|---:|
| Segmentation | 1 | 999 |
| Reconstruction | 1 | 999 |
| Classification | 2 | 998 |
| Image Registration | 1 | 999 |
| Domain Adaptation | 0 | 1000 |
| Generative Models | 2 | 998 |
| General | 0 | 1000 |
<!-- END COVERAGE_REPORT -->

## 🔬 Browse the Index

### Task-based browse

The seven canonical task categories. Each entry links to the corresponding section below.

| Category | Description |
|---|---|
| [Segmentation](#segmentation) | Pixel- and voxel-level segmentation of anatomical structures and lesions. |
| [Reconstruction](#reconstruction) | Image reconstruction, denoising, super-resolution, restoration. |
| [Classification](#classification) | Image-, region-, and patch-level classification and recognition. |
| [Image Registration](#image-registration) | Inter- and intra-patient registration, alignment, deformable models. |
| [Domain Adaptation](#domain-adaptation) | Cross-domain generalization, transfer learning, domain shift. |
| [Generative Models](#generative-models) | Diffusion, GAN, VAE, flow-matching, score-based generative approaches. |
| [General](#general) | Papers that don't strongly match any specific task label. |

### Modality-based browse

A separate multi-label modality classification is generated for each paper (`dist/modalities.json`). The canonical modalities tracked today are: **MRI**, **CT**, **X-Ray**, **Ultrasound**, **Pathology**, **OCT**, **PET**, **Endoscopy**, **Dermoscopy**, **Microscopy**, **Fundus**.

### Method-based browse

Multi-label method classification (`dist/methods.json`) covers **Transformer / Swin / ViT**, **CNN**, **Diffusion**, **GAN**, **Foundation Model**, **SAM-family**, **Vision-Language Model**, **Mamba / SSM**, **Federated Learning**, **Self-Supervised**, **Few-Shot**, **Zero-Shot**, **Semi-Supervised**.

### Track-based browse

Tracks are detected from title/abstract/comment evidence and recorded in the paper's `track` field (`main` / `workshop` / `challenge` / `tutorial` / `dataset` / `unknown`). Per-track counts are in [`dist/index.json`](./dist/index.json).

## 🤝 How to Contribute

Contributions are welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full workflow. The short version:

- 🐛 **Report errors** — broken links, wrong conference attribution, wrong category, missing paper.
- 🏷️ **Suggest taxonomy improvements** — open an issue with concrete examples; do not edit `config/taxonomy.yaml` in a feature PR.
- 📝 **Add a paper manually** — open an issue with the arXiv ID and the conference evidence (e.g. `Accepted to MICCAI 2026`). Maintainers will add it through the pipeline so provenance is preserved.
- 💡 **Propose new data sources** — open an issue describing the source, expected fields, and rate limits.

All contributions must respect the inclusion policy and provide evidence.

## 📊 Project Stats

The pipeline emits aggregate statistics on every run (see `dist/statistics.json`). Selected fields:

- `papers_total`, `papers_with_code`, `papers_unique`, `papers_uncertain`
- `papers_by_track`, `papers_by_repository_host`
- `fetched_records`, `filtered_non_target`, `filtered_track`, `filtered_no_code`, `duplicates_removed`
- `papers_added_since_last_run`, `papers_removed_since_last_run`, `papers_updated_since_last_run`

These are reproducible from the canonical dataset.

## ⚠️ Disclaimer

Inclusion in this index is **not an endorsement**. Code is included if a paper's arXiv metadata points to a public repository; the repository is not reviewed for quality, correctness, or license compatibility with downstream use. Authors retain copyright of their work.

## 📜 License

- Repository metadata, taxonomy, and pipeline source: [Apache License 2.0](./LICENSE).
- Paper metadata is sourced from arXiv and is subject to [arXiv's terms of use](https://arxiv.org/help/license).
- Code repository URLs are links; the linked code is owned by its respective authors.

---

**Conference Scope**: miccai-all-years
**Discovery Mode**: broad
**Last Updated**: 2026-09-28 15:58 UTC by GitHub Actions

---

# 📚 Generated Index (preserved content)

*The section below is automatically generated by the pipeline from the canonical dataset. Content between `<!-- BEGIN … -->` and `<!-- END … -->` markers is overwritten on every successful build.*

## 📊 Segmentation

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN SEGMENTATION_PAPERS -->
* **[Brain Tumor Segmentation with Diffusion Models](https://arxiv.org/abs/2608.00001v1)** - [Code](https://github.com/alice/brain-seg-diffusion) (confidence: high)
<!-- END SEGMENTATION_PAPERS -->

## 📊 Reconstruction

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN RECONSTRUCTION_PAPERS -->
* **[Mamba-Based Reconstruction for Sparse-View CT](https://arxiv.org/abs/2608.00004v1)** - [Code](https://github.com/eve/mamba-ct-recon) (confidence: high)
<!-- END RECONSTRUCTION_PAPERS -->

## 📊 Classification

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN CLASSIFICATION_PAPERS -->
* **[Federated Learning for Pathology Image Analysis](https://arxiv.org/abs/2608.00003v1)** - [Code](https://github.com/dave/fed-path) (confidence: high)
* **[Vision Transformer for CT Lung Nodule Classification](https://arxiv.org/abs/2608.00002v1)** - [Code](https://github.com/carol/vit-ct-classifier) (confidence: high)
<!-- END CLASSIFICATION_PAPERS -->

## 📊 Image Registration

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN IMAGE_REGISTRATION_PAPERS -->
* **[Deformable Image Registration using Diffusion Priors](https://arxiv.org/abs/2608.00005v1)** - [Code](https://github.com/frank/diffreg) (confidence: high)
<!-- END IMAGE_REGISTRATION_PAPERS -->

## 📊 Domain Adaptation

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN DOMAIN_ADAPTATION_PAPERS -->
<!-- END DOMAIN_ADAPTATION_PAPERS -->

## 📊 Generative Models

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN GENERATIVE_MODELS_PAPERS -->
* **[Deformable Image Registration using Diffusion Priors](https://arxiv.org/abs/2608.00005v1)** - [Code](https://github.com/frank/diffreg) (confidence: high)
* **[Brain Tumor Segmentation with Diffusion Models](https://arxiv.org/abs/2608.00001v1)** - [Code](https://github.com/alice/brain-seg-diffusion) (confidence: high)
<!-- END GENERATIVE_MODELS_PAPERS -->

## 📊 General

*This list is automatically generated. See any issues? Please open a pull request!*

<!-- BEGIN GENERAL_PAPERS -->
<!-- END GENERAL_PAPERS -->
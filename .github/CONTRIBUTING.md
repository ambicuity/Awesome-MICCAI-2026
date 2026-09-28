# Contributing to Awesome MICCAI 2026

Thank you for your interest in contributing to this curated list of MICCAI papers with public code!

## 🤖 How This Repository Works

This repository is **bot-maintained**. A GitHub Actions workflow runs daily to:

1. Search arXiv for papers mentioning "MICCAI"
2. Extract papers that have public code repositories (GitHub, GitLab, Hugging Face)
3. Normalize and validate repository links
4. Apply weighted multi-label categorization with explicit evidence
5. Regenerate the README, data products, and validation report

If any quality gate fails, the workflow fails and no update is committed.

**Important:** Manual edits to auto-generated sections in `README.md` will be overwritten by the bot.

The pipeline is **PR-based**: the daily workflow opens a pull request with the diff instead of force-pushing to `main`.

## 👥 Human Contributions

Human contributions are welcome for **quality control and oversight**. Your help ensures accuracy and completeness of the list.

### Ways to Contribute

| Contribution Type | How to Help |
|------------------|-------------|
| 🐛 **Report incorrect paper** | Not MICCAI, stale entry, wrong metadata, malformed/broken link |
| ➕ **Add missing paper** | Bot missed a valid MICCAI paper with code |
| 🔗 **Fix broken link** | Code repository link no longer works |
| 🏷️ **Suggest category change** | Paper is in the wrong category |
| 🧬 **Suggest taxonomy change** | New task / modality / method label is needed |
| 🛠️ **Improve the pipeline** | Bug fix, performance, observability |

## 📋 Before Contributing

- Read [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) to understand the system.
- Read [`docs/DATA_MODEL.md`](../docs/DATA_MODEL.md) to understand the schema.
- Read [`docs/TAXONOMY.md`](../docs/TAXONOMY.md) to understand classification.
- Search existing issues before opening a new one.

## 🐛 Reporting Issues

When reporting an issue, please include:

1. The arXiv ID of the paper.
2. The category / track where it appears (or should appear).
3. Why the current state is wrong.
4. Evidence supporting your position (e.g., link to arXiv comment, link to repository).

## ➕ Adding a Paper Manually

The bot cannot manually inject papers (to preserve provenance). To add a paper:

1. Open an issue with the arXiv ID and the conference evidence line.
2. A maintainer will run `python -m miccai_index build --offline` and open a PR with the data diff.

## 🏷️ Suggesting a Category Change

The taxonomy is configured in `config/taxonomy.yaml`. To propose a change:

1. Open an issue describing the label.
2. Provide 2-3 example papers that should match.
3. Propose 2-3 example regex rules with weights.

Maintainers will evaluate and merge.

## 🛠️ Improving the Pipeline

To submit code changes:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/my-change`).
3. Add tests for new behavior under `tests/`.
4. Ensure `make test` passes.
5. Ensure `make validate-offline` passes.
6. Open a PR describing the rationale and tradeoffs.

## 📝 Style Guide

- Python: follow PEP 8; type hints are required for new public APIs.
- YAML: 2-space indentation, no tabs.
- Markdown: 80-character line soft wrap in prose; tables aligned.

## 🔒 Security

See [`SECURITY.md`](../SECURITY.md) for reporting security issues.

## 📜 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
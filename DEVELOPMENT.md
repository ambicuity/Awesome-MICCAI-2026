# Development Setup

This document walks a new contributor through setting up a development environment for the MICCAI index.

## Prerequisites

* Python 3.10 or newer.
* `git`.
* (Optional) `pyenv` or `conda` for managing Python versions.

## Quick setup

```bash
git clone https://github.com/ambicuity/Awesome-MICCAI-2026
cd Awesome-MICCAI-2026
make setup
```

`make setup` installs the runtime dependency (`arxiv`) using `pip`. There is no separate dev-requirements file because the test suite uses only the standard library.

## Running tests

```bash
make test                 # full suite
make test-unit            # unit tests
make test-integration     # integration tests with mocked sources
make test-property        # property / invariant tests
```

## Running the pipeline

```bash
make build                # full build (network required)
make build-offline        # offline render from existing data
make report               # print analytics
```

## Project layout

```
.
├── src/miccai_index/     # the new pipeline package
├── scripts/              # legacy scripts (still works as a compat wrapper)
├── tests/                # unit + integration + property tests
├── schemas/              # canonical JSON Schemas
├── config/               # YAML configuration
├── data/                 # canonical dataset (papers.jsonl, repositories.jsonl)
│   └── snapshots/        # immutable source snapshots
├── dist/                 # generated data products
├── docs/                 # architecture, data model, taxonomy docs
└── .github/              # workflow and templates
```

## Coding conventions

* Python 3.10+ syntax (match/case, structural pattern matching).
* Type hints are required for all new public APIs.
* Docstrings use reStructuredText style; the first line is a one-line summary.
* Imports are sorted: stdlib, third-party, local.
* No external dependencies beyond `arxiv`. If you need a new dep, justify it in the PR.

## Submitting changes

1. Create a feature branch.
2. Run `make test` and `make validate-offline` locally.
3. Open a PR. CI will run the same checks.

## Debugging tips

* `python -m miccai_index discover --scope miccai-all-years --mode broad` — shows discovery metadata without writing.
* `python -m miccai_index validate --offline --verbose` — verbose validation.
* Inspect `data/changelog.jsonl` to see what changed in the last run.
* Inspect `dist/statistics.json` for aggregate metrics.

## Common pitfalls

* **YAML escape sequences in patterns.** Patterns like `\bsegmentation\b` must be double-quoted in YAML (`"\bsegmentation\b"`) to preserve backslashes. Single-quoted strings keep backslashes literal.
* **Conference scope semantics.** `miccai-2026` requires the paper to mention 2026 (or `'26`). `miccai-all-years` accepts any MICCAI year.
* **The pipeline never deletes data on failure.** If a build fails, the previous `data/papers.jsonl` is preserved.
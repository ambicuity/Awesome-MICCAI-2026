# AGENTS.md — instructions for AI coding agents

This file is the entry point for AI coding agents (Claude Code, Codex, Cursor,
Aider, Gemini CLI, Devin, OpenCode, etc.) working in this repository.

> **Claude-specific instructions live in [CLAUDE.md](./CLAUDE.md).**
> If your agent only reads `AGENTS.md`, the instructions below apply.

## What this project is

A reproducible, schema-validated pipeline that discovers MICCAI papers from
arXiv, normalizes them, classifies them with a multi-label taxonomy, and
renders both a human-readable README and a set of machine-readable data
products. The README is one rendered view of a much richer canonical
dataset under `data/` and `dist/`.

The pipeline is **deterministic** (byte-stable per input snapshot), **incremental**
(cache + content-hash snapshots), **observable** (structured stats + JSONL
changelog), and **safe** (a degraded run never silently overwrites good data).

Detailed design lives under [`docs/`](./docs/):

| Document | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Layered architecture, determinism guarantees, extension points. |
| [`docs/DATA_MODEL.md`](./docs/DATA_MODEL.md) | Field-by-field schema, invariants, provenance. |
| [`docs/TAXONOMY.md`](./docs/TAXONOMY.md) | How classification works and how to add labels. |
| [`docs/DATA_SOURCES.md`](./docs/DATA_SOURCES.md) | External sources, rate limits, future roadmap. |
| [`docs/AUTOMATION.md`](./docs/AUTOMATION.md) | GitHub Actions, PR-based daily update, secrets. |
| [`docs/quality.md`](./docs/quality.md) | Paper-quality dimensions, why we don't ship a single score. |

## Build, test, and validate

The project ships a `Makefile` so every contributor reproduces the same
workflow locally. The commands are the source of truth — keep them working.

```bash
make setup             # install the single runtime dependency (arxiv)
make test              # full test suite (98 tests; unit + integration + property)
make validate          # schema-validate canonical data + check README markers
make validate-offline  # same as validate, but no network calls
make build             # full pipeline (network required)
make build-offline     # render README + dist/ from existing data only
make report            # analytics over the canonical dataset
make clean             # remove generated artifacts
```

Direct CLI (when you need finer control):

```bash
PYTHONPATH=src python -m miccai_index --help
PYTHONPATH=src python -m miccai_index build --scope miccai-all-years --mode broad --tracks all
PYTHONPATH=src python -m miccai_index --offline validate --scope miccai-all-years --mode broad --tracks all
PYTHONPATH=src python -m miccai_index --offline report  --scope miccai-all-years --mode broad --tracks all
```

The `--offline` flag is a global flag; it must come **before** the subcommand.

## Project layout

```
.
├── AGENTS.md                       ← you are here
├── CLAUDE.md                       ← Claude-specific configuration
├── README.md                       ← one rendered view of the canonical dataset
├── LICENSE                         ← Apache 2.0
├── Makefile                        ← reproducible entry points
├── DEVELOPMENT.md                  ← dev environment setup
├── SECURITY.md                     ← security policy
│
├── src/miccai_index/               ← the new pipeline package (Python)
│   ├── __init__.py
│   ├── __main__.py                 ← enables `python -m miccai_index`
│   ├── errors.py                   ← structured error taxonomy
│   ├── config.py                   ← typed config objects
│   ├── config_loader.py            ← minimal YAML subset loader (no PyYAML dep)
│   ├── normalization/              ← arXiv ID + repository URL canonicalization
│   ├── conference_evidence.py      ← evidence-based conference detection
│   ├── classification.py           ← multi-label taxonomy classifier
│   ├── quality.py                  ← per-paper quality dimensions
│   ├── health.py                   ← pipeline health threshold check
│   ├── cache.py                    ← filesystem cache + snapshots
│   ├── sources/                    ← external source adapters
│   ├── discovery.py                ← end-to-end pipeline orchestration
│   ├── storage.py                  ← JSONL I/O
│   ├── changelog.py                ← run-to-run diff
│   ├── validation.py               ← JSON Schema validation
│   ├── rendering/                  ← README + data products
│   └── cli.py                      ← argparse CLI
│
├── scripts/                        ← legacy entry points (preserved)
│   ├── update_papers.py            ← thin wrapper around `python -m miccai_index build`
│   └── validate_readme.py          ← legacy README-marker validator
│
├── tests/                          ← unit + integration + property tests
│
├── schemas/                        ← canonical JSON Schemas
│   ├── paper.schema.json
│   ├── repository.schema.json
│   └── index.schema.json
│
├── config/                         ← policy as YAML (no recompile to change)
│   ├── conference.yaml             ← conference scope, evidence levels, tracks
│   ├── taxonomy.yaml               ← labels + regex rules for classification
│   ├── sources.yaml                ← source adapters (network policy + queries)
│   └── validation.yaml             ← health thresholds, required fields
│
├── data/                           ← canonical dataset (JSONL)
│   ├── papers.jsonl                ← one paper per line, schema-validated
│   ├── repositories.jsonl          ← one repo per line, schema-validated
│   ├── changelog.jsonl             ← run-to-run diff events
│   └── snapshots/                  ← immutable source snapshots
│
├── dist/                           ← generated machine-readable products
│   ├── papers.json / papers.jsonl  ← canonical dataset (mirror of data/)
│   ├── repositories.json
│   ├── categories.json             ← per-category counts
│   ├── modalities.json             ← per-modality counts
│   ├── methods.json                ← per-method counts
│   ├── datasets.json               ← per-dataset counts
│   ├── statistics.json             ← aggregate pipeline stats
│   ├── search-index.json           ← ready-to-consume search index
│   └── index.json                  ← top-level manifest
│
├── docs/                           ← design documentation (Markdown)
│
└── .github/
    ├── workflows/
    │   ├── ci.yml                  ← test + offline validate on every PR
    │   └── update-data.yml         ← daily cron + manual dispatch → opens a PR
    ├── CONTRIBUTING.md             ← human contribution workflow
    ├── ISSUE_TEMPLATE/
    └── PULL_REQUEST_TEMPLATE.md
```

## Core invariants

The pipeline is built around a few hard rules. **Do not violate them.**

1. **Provenance first.** Every paper record carries `provenance.sources`,
   `provenance.fetched_at`, and a `conference_evidence` array. Never invent
   papers, authors, repositories, or classifications.
2. **Schema before render.** Any code that writes to `data/papers.jsonl` or
   `data/repositories.jsonl` MUST run the JSON-Schema validator first.
   See [`src/miccai_index/validation.py`](./src/miccai_index/validation.py).
3. **Determinism.** Outputs are byte-stable for a given `(config, source
   snapshot)`. Avoid Python set/dict iteration order leaking into JSON output.
   All JSONL is written with `sort_keys=True`.
4. **Never overwrite good data on failure.** The health threshold in
   `config/validation.yaml` (`health.minimum_coverage_ratio`) prevents a
   degraded discovery run from clobbering the canonical dataset. The CLI
   build subcommand enforces this; do not bypass it.
5. **Conference evidence is structured.** Do not add papers based on raw
   keyword matches. Use the evidence model in
   [`src/miccai_index/conference_evidence.py`](./src/miccai_index/conference_evidence.py).
6. **Multi-label taxonomy, weighted rules.** A paper can belong to multiple
   tasks / modalities / methods. Each label has a confidence in `[0, 1]`.
   See [`docs/TAXONOMY.md`](./docs/TAXONOMY.md).
7. **PR-only daily automation.** The `update-data` workflow opens a PR; it
   must never force-push to `main`. See
   [`docs/AUTOMATION.md`](./docs/AUTOMATION.md).
8. **Backward compatibility.** `scripts/update_papers.py` and
   `scripts/validate_readme.py` are public contracts. Don't break them;
   add the new behavior in `src/miccai_index/` and update the wrappers.

## Common tasks for agents

### Add a new taxonomy label

1. Edit `config/taxonomy.yaml` — add an entry under `tasks:`, `modalities:`,
   `methods:`, or `datasets:`. Provide ≥ 1 regex rule with a non-zero weight.
2. Run `make test-unit` — unit tests should pass unchanged.
3. Run `make build-offline` — verify the new label appears in
   `dist/modalities.json` (or the appropriate file).
4. Open a PR with the YAML change and the regenerated `dist/`. Reference the
   example paper IDs in the PR description so reviewers can sanity-check.

### Add a new external source

1. Implement a class with `.id`, `.is_enabled()`, and
   `.fetch(queries, ...)` returning `(records, metadata)`. Mirror the
   contract in [`src/miccai_index/sources/arxiv_source.py`](./src/miccai_index/sources/arxiv_source.py).
2. Add a config block to `config/sources.yaml`.
3. Register the adapter in `src/miccai_index/cli.py:_make_arxiv_source`.
4. Add unit + integration tests using a mocked transport.
5. Do not add an LLM client, code-execution sandbox, or any dep that
   requires an API key as a hard dependency.

### Change a confidence threshold or health policy

Edit `config/validation.yaml`. The validator and the health-check code read
the config at runtime — no recompile required.

### Fix a bug in classification or normalization

1. Add a failing test under `tests/` (unit, integration, or property —
   whichever most clearly expresses the invariant).
2. Fix the bug.
3. Re-run `make test` and `make validate-offline`.
4. If you touched normalization, also run `make build-offline` and inspect
   the regenerated README + `dist/` for regressions.

## Conventions

### Python

* Python 3.10+ syntax (structural pattern matching is OK).
* Type hints are required for all new public APIs.
* Public functions get a docstring; the first line is a one-line summary.
* Imports: stdlib, third-party, local — separated by blank lines.
* One external runtime dependency: `arxiv`. Do not add others unless the
  alternative (stdlib only) is materially worse.
* No `print` statements in production code; use the logger or write to
  `sys.stderr` via the CLI entry point.

### YAML

* 2-space indentation, no tabs.
* Use double-quoted strings for regex patterns that contain backslashes
  (e.g. `pattern: "\bsegmentation\b"`). Single-quoted strings keep
  backslashes literal.
* Comments start with `#` and may appear on their own line or at the end
  of a line.

### Markdown

* 80-character soft wrap for prose.
* Tables should be aligned.
* Generated content goes inside `<!-- BEGIN ... -->` / `<!-- END ... -->`
  markers. Everything outside is hand-written prose.

### Git

* One feature per PR; keep diffs reviewable.
* Commit author identity must NOT contain `mavis`, `Mavis`, or `MiniMax`
  — this is a stable user preference. If the local git identity is
  contaminated, override per-commit with:
  `git -c user.name="<name>" -c user.email="<email>" commit …`
* Never commit secrets, API keys, or credentials. The pipeline does not
  require any.

## What NOT to do

* **Do not** invent papers, authors, repositories, or classifications. If
  something is uncertain, leave it out or record the uncertainty explicitly.
* **Do not** silently broaden the conference scope. The default is
  `miccai-all-years`; the strict 2026 scope must be explicitly requested.
* **Do not** silently drop records. Removing a paper from the dataset
  requires an explicit, auditable reason.
* **Do not** introduce an LLM dependency. The taxonomy is rule-based and
  deterministic; an optional semantic layer can be added later behind a
  config flag.
* **Do not** bypass tests to make CI green. If a test fails, fix the code
  or fix the test — never silence it.
* **Do not** add hard-coded secrets, API keys, or tokens. The pipeline
  needs none.
* **Do not** add a new external runtime dependency without justification
  and discussion in the PR.
* **Do not** modify generated content (`data/`, `dist/`, README marker
  blocks) by hand. The pipeline regenerates them; manual edits are
  overwritten.

## Asking the user

When you genuinely cannot decide, ask the user — but only about decisions
that materially change the result. Most policy questions are answered by
the config files (`config/*.yaml`). Most architecture questions are
answered by the docs (`docs/*.md`). Read those before asking.

The kinds of questions worth asking:

* "Should we add a new external source?" — yes, this is a policy decision.
* "Should we lower the conference_evidence minimum for `miccai-2026`?" —
  this changes inclusion semantics, ask first.
* "Should we expose a new search dimension?" — this is a UX/API decision.

The kinds of questions NOT worth asking:

* "Which Python version should I target?" — `python_requires` and the
  `Makefile` answer this.
* "Should I add tests?" — yes, always.
* "Should I update docs when I change code?" — yes, always.

## Quick reference — file map for common questions

| If the user asks about… | Look at… |
|---|---|
| How is the pipeline structured? | `docs/ARCHITECTURE.md` |
| What fields does a paper record have? | `docs/DATA_MODEL.md` + `schemas/paper.schema.json` |
| How are papers classified? | `docs/TAXONOMY.md` + `src/miccai_index/classification.py` |
| Why was this paper included? | The paper's `conference_evidence` array in `data/papers.jsonl` |
| How does the daily update work? | `docs/AUTOMATION.md` + `.github/workflows/update-data.yml` |
| How is the README generated? | `src/miccai_index/rendering/readme.py` |
| Where do data products live? | `dist/` (see the README "Quick Links" section) |
| What is the trust model? | `docs/DATA_SOURCES.md`, `SECURITY.md`, this file |
| How do I add a label? | "Add a new taxonomy label" above |
| How do I add a source? | "Add a new external source" above |

## Final notes

This file is the contract between human maintainers and AI agents. If you
change something that affects how agents should work (new entry points,
new invariants, new docs), update this file in the same PR.

If you find an instruction in this file that conflicts with the code, the
code is correct and the instruction is wrong — but fix the instruction
too, so the next agent does not get confused.
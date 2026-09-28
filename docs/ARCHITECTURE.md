# Architecture

This document describes the runtime architecture of the MICCAI research index pipeline. It is the source of truth for *how* the pipeline is structured; *why* it is structured that way is in [`DATA_MODEL.md`](./DATA_MODEL.md).

## High-level view

```
                ┌─────────────────────────────┐
                │  External Research Sources  │
                │ arXiv (primary)             │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │   Discovery + Ingestion     │   src/miccai_index/sources/
                │ cache-first, retry, backoff │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │ Normalization / Resolution   │   src/miccai_index/normalization/
                │ arXiv ID, repository URL,   │   src/miccai_index/conference_evidence.py
                │ conference evidence         │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │ Classification + Enrichment  │   src/miccai_index/classification.py
                │ taxonomy / modality / task   │   src/miccai_index/quality.py
                │ dataset / method / conf.    │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │  Quality / Trust Pipeline    │   src/miccai_index/validation.py
                │ schema, referential, drift   │
                └──────────────┬──────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        canonical data     README.md        data products
        data/papers.jsonl  (dist/)          (dist/)
              │
              ├──────────────► search-index.json
              │
              ├──────────────► changelog.jsonl
              │
              └──────────────► analytics (statistics.json)
```

## Layered design

The package is layered. Each layer depends on the layers below it; nothing depends on the layers above it.

| Layer | Module(s) | Responsibility |
|---|---|---|
| Errors | `errors.py` | Structured exception taxonomy (`IndexError_`, `DiscoveryError`, `RateLimitError`, `SourceFormatError`, `ValidationError`, `ConfigurationError`, `RepositoryResolutionError`, `GenerationError`). |
| Config | `config.py`, `config_loader.py` | Load YAML configuration into typed objects (`ConferenceConfig`, `TaxonomyConfig`, `SourcesConfig`, `ValidationConfig`). |
| Cache | `cache.py` | Filesystem-backed JSON cache with content-hash keys and TTL. |
| Schemas | `schemas/*.json` | Canonical JSON Schemas for paper, repository, and index records. |
| Validation | `validation.py` | Schema validator (stdlib-only), referential integrity checks. |
| Normalization | `normalization/arxiv.py`, `normalization/repository.py`, `conference_evidence.py` | URL canonicalization, arXiv ID parsing, conference-evidence detection. |
| Classification | `classification.py`, `quality.py` | Multi-label taxonomy classification with per-label confidence, paper-quality metrics. |
| Sources | `sources/arxiv_source.py` | Source adapters (cache-first, retries, structured errors). |
| Discovery | `discovery.py` | Orchestrates the end-to-end pipeline. |
| Storage | `storage.py`, `changelog.py` | JSONL read/write, change tracking between runs. |
| Rendering | `rendering/readme.py`, `rendering/data_products.py` | README + `dist/` artifact generation. |
| CLI | `cli.py` | Argument parsing, subcommands, offline mode. |

## Determinism

The pipeline is deterministic with respect to:

* Source snapshot. A given arXiv API response always yields the same `ArxivRecord` set.
* Configuration. Taxonomy, sources, and validation rules are loaded from YAML.
* Time. Timestamps are written into data products only as metadata; they do not influence ordering or classification.

For a given `(config, source_snapshot)`, the output is byte-for-byte identical across runs, machines, and Python versions.

## Incremental processing

The pipeline avoids re-fetching and re-processing:

* **Cache** — `cache.py` stores source responses keyed by content hash. Re-runs read from cache when fresh.
* **Snapshots** — `data/snapshots/` keeps timestamped bundles of source data for reproducibility.
* **Diffing** — `changelog.py` diffs the previous and current canonical dataset to emit per-paper events without rewriting unchanged records.

## Failure handling

The pipeline fails safely:

* A partial upstream failure is logged but does not crash the run; the last known good canonical dataset is preserved on disk.
* A schema-invalid paper is reported as a structured error and excluded from `data/papers.jsonl`.
* CI runs `python -m miccai_index validate` on every PR; failing validation prevents merging.

## CLI

`python -m miccai_index <subcommand> [flags]`

| Subcommand | Network? | Description |
|---|---|---|
| `discover` | yes | Run discovery only; print metadata. |
| `normalize` | yes | Run discovery + normalization; write `data/papers.jsonl`. |
| `classify` | no | Re-run classification over an existing dataset. |
| `validate` | no | Validate existing data products. |
| `render` | no | Render README from canonical data. |
| `build` | yes | Full pipeline: discover → normalize → validate → render → products. |
| `update` | yes | Alias for `build`. |
| `report` | no | Print analytics. |

Global flags: `--offline`, `--dry-run`, `--config-dir DIR`, `--verbose`.

## Extension points

* **New source adapter**: implement a class with `.id`, `.is_enabled()`, `.fetch(ctx, queries)` returning `(records, metadata)`. Add a config block under `config/sources.yaml`. Register it in `cli.py`.
* **New taxonomy label**: add an entry under `tasks/`, `modalities/`, or `methods/` in `config/taxonomy.yaml`. The classifier picks it up automatically.
* **New render output**: add a `DistProduct` in `rendering/data_products.py` and append it to the build output list.

## Operational guarantees

1. The pipeline never silently overwrites good data with a partial result.
2. The pipeline never invents papers, repositories, authors, or categories.
3. The pipeline is reproducible offline given an existing `data/papers.jsonl`.
4. Every classification decision is traceable through the rule weight + matched pattern.
5. Every conference decision is traceable through the structured `conference_evidence` records on the paper.

For the schema definitions, see [`DATA_MODEL.md`](./DATA_MODEL.md).
For the rule-based taxonomy, see [`TAXONOMY.md`](./TAXONOMY.md).
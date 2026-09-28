# Data Model

The canonical dataset is `data/papers.jsonl`. Each line is a JSON object conforming to [`schemas/paper.schema.json`](../schemas/paper.schema.json). This document explains each field, the reasoning behind it, and the invariants we maintain.

## Top-level paper record

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable canonical identifier (`arxiv:<id>`, `doi:<id>`, or `uuid:<id>`). |
| `title` | string | Paper title (verbatim from source). |
| `abstract` | string | Abstract text (may be empty if not exposed by the source). |
| `authors` | array of `{name, affiliation?, orcid?}` | Author list. |
| `identifiers` | object | Map of source identifier payloads (`arxiv`, `doi`, etc.). |
| `venue` | object | `{name, year, track, acm?, openalex?}`. |
| `track` | enum | `main` \| `workshop` \| `challenge` \| `tutorial` \| `dataset` \| `unknown`. |
| `categories` | array | Multi-label task classification. |
| `modalities` | array | Multi-label modality classification. |
| `methods` | array | Multi-label method classification. |
| `datasets` | array | Dataset mentions (canonical names). |
| `keywords` | array | Lightweight extracted keywords. |
| `repositories` | array | Repository objects (see below). |
| `conference_evidence` | array | Records explaining why a paper is in scope. |
| `confidence` | object | Per-dimension confidence values in `[0, 1]`. |
| `provenance` | object | `{sources, fetched_at, snapshot_id, notes}`. |
| `quality` | object | Per-dimension quality metrics (see [`quality.md`](./quality.md)). |
| `timestamps` | object | `{created_at, updated_at}` — metadata only, not used for ordering. |

## Identifiers

```json
{
  "arxiv": {
    "id": "2608.13223",
    "version": "v3",
    "url": "https://arxiv.org/abs/2608.13223v3",
    "published": "2026-01-01T00:00:00Z",
    "updated": "2026-01-15T00:00:00Z",
    "comment": "Accepted to MICCAI 2026"
  }
}
```

* Multiple arXiv versions (`v1`, `v2`, ...) share the same `arxiv.id` (base) and differ only in `arxiv.version`. The canonical paper ID is `arxiv:<base_id>`, ignoring version.
* `arxiv.url` always uses the canonical absolute URL form.

## Conference evidence

```json
{
  "conference_evidence": [
    {"source": "arxiv_comment", "match": "Accepted to MICCAI 2026", "strength": "EXPLICIT_STRONG"},
    {"source": "arxiv_title",    "match": "MICCAI 2024 Challenge",  "strength": "EXPLICIT"}
  ]
}
```

The five strength levels, from strongest to weakest:

| Level | Meaning | Examples |
|---|---|---|
| `EXPLICIT_STRONG` | Direct acceptance / publication statement. | `Accepted to MICCAI 2026`, `Camera-ready: MICCAI 2026` |
| `EXPLICIT` | Clear year-marked mention. | `MICCAI 2026`, `MICCAI '26` |
| `INFERRED` | MICCAI mentioned, no year. | `MICCAI workshop`, `MICCAI dataset` |
| `WEAK` | Submission wording only. | `Submitted to MICCAI` |
| `UNKNOWN` | No match. | — |

A paper is included in a scope only when its strongest evidence meets or exceeds the scope's configured minimum. See [`TAXONOMY.md`](./TAXONOMY.md) for the configuration.

## Repositories

```json
{
  "id": "github:user/repo",
  "url": "https://github.com/user/repo",
  "host": "github.com",
  "owner": "user",
  "name": "repo",
  "relationship": "official_implementation",
  "confidence": "high",
  "evidence": ["url_found_in_arxiv_comment"],
  "verification": {
    "status": "unverified",
    "checked_at": "2026-04-05T01:28:00Z",
    "source": "pipeline"
  }
}
```

| Relationship | Description |
|---|---|
| `official_implementation` | Linked by the paper authors as the canonical implementation. |
| `author_implementation` | Repository owned by a paper author, but not officially linked. |
| `unofficial_reimplementation` | Reimplementation by a third party. |
| `dataset_repository` | Dataset only. |
| `project_page` | Project page rather than code repository. |
| `model_checkpoint` | Model weights or checkpoint host. |
| `demo` | Interactive demo. |
| `unknown` | Unclassified. |

The `id` is stable across URL forms (`tree/main`, `blob/main/README.md`, `https` vs `git`). All URLs are canonicalized to `https://<host>/<owner>/<name>` before storage.

## Confidence

```json
{
  "overall": 0.85,
  "tasks": {"segmentation": 0.9, "reconstruction": 0.5},
  "modalities": {"mri": 0.85},
  "methods": {"transformer": 0.7}
}
```

* `overall` is derived from the strongest conference-evidence level.
* Per-dimension confidences are derived from accumulated rule weights (normalized against 2× the label's threshold).

## Quality

```json
{
  "metadata_completeness": 0.8,
  "repository_accessibility": 0.5,
  "conference_evidence_strength": 0.85,
  "classification_confidence": 0.78,
  "duplicate_risk": 0.0,
  "freshness_days": 12.4,
  "freshness_score": 0.98
}
```

Each dimension is independent — there is no single "paper score". See [`quality.md`](./quality.md) for details.

## Repository record

```json
{
  "id": "github:user/repo",
  "host": "github.com",
  "owner": "user",
  "name": "repo",
  "url": "https://github.com/user/repo",
  "papers": ["arxiv:2608.13223"],
  "verification": {"status": "unverified", "checked_at": "", "source": ""},
  "timestamps": {"first_seen": "2026-04-05T01:28:00Z", "last_seen": "2026-04-05T01:28:00Z"}
}
```

## Index manifest

[`dist/index.json`](../dist/index.json) is the top-level manifest:

```json
{
  "version": "0.2.0",
  "schema_version": "1.0.0",
  "generated_at": "2026-04-05T01:28:00Z",
  "conference": {"name": "MICCAI", "year": 2026},
  "statistics": {"papers_total": 784, ...},
  "tracks": {"main": 700, "workshop": 50, ...},
  "categories": {"Segmentation": 351, ...},
  "modalities": {"MRI": 120, ...},
  "methods": {"Transformer": 80, ...},
  "datasets": {"BraTS": 30, ...},
  "repository_hosts": {"github.com": 760, "gitlab.com": 15, "huggingface.co": 9}
}
```

## Schema versioning

The schema is versioned. The current version is `1.0.0`. The supported versions are listed in `config/validation.yaml`. When the schema changes in a backwards-incompatible way, the major version is bumped and a migration path is documented here.

## Invariants

These invariants are checked at validation time:

1. Every paper has a unique `id`.
2. Every repository reference in a paper resolves to a repository record.
3. Every paper category is in the configured taxonomy.
4. Every repository URL is parseable and on an allowed host.
5. Every confidence value is in `[0, 1]`.
6. Every required field is present and non-empty.
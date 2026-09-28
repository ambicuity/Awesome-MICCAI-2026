# Paper Quality Metrics

The MICCAI index exposes per-paper **quality dimensions** rather than a single opaque "score". Each dimension is documented, reproducible from the paper record, and tunable via configuration.

## Dimensions

| Dimension | Range | Description | Computation |
|---|---|---|---|
| `metadata_completeness` | `[0, 1]` | Are abstract, authors, DOI, and repositories present? | `0.4 * has_abstract + 0.2 * has_authors + 0.2 * has_doi + 0.2 * has_repositories` |
| `repository_accessibility` | `[0, 1]` | Are repositories linked and likely reachable? | `min(1.0, repository_count / 2.0)` |
| `conference_evidence_strength` | `[0, 1]` | Strongest conference-evidence level. | Mapped from the `overall` confidence. |
| `classification_confidence` | `[0, 1]` | Mean per-label confidence across all dimensions. | `mean(tasks.values(), modalities.values(), methods.values())` |
| `duplicate_risk` | `[0, 1]` | Likelihood that the paper is a duplicate. | Currently `0.0`; filled in by future dedup pass. |
| `freshness_days` | days | Days since the paper was published. | `now - published_at`. |
| `freshness_score` | `[0, 1]` | Linear decay from publication. | `max(0, 1 - freshness_days / 730)` |

## Why not a single score?

A single score invites the temptation to rank papers by it. Ranking papers is:

* Not what an **index** does. The role of an index is to surface candidates for human evaluation.
* Sensitive to bad incentives: any scoring function can be gamed by authors who know the function.
* Opaque: even if we showed the formula, a single number hides the underlying evidence.

The dimensions we expose are deliberately diagnostic. Each one tells a maintainer what to look at when triaging a paper.

## What this is not

* This is **not** a paper-ranking system.
* This is **not** a citation metric. We don't track citations.
* This is **not** an indication of paper quality. Inclusion in the index is not an endorsement.

## Configuration

The quality module has no external configuration today. To change behavior, edit `src/miccai_index/quality.py` directly.

## Reproducibility

All dimensions are computed deterministically from the paper record. The same `quality` input always produces the same output, byte-for-byte.
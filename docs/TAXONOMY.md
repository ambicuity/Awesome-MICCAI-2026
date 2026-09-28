# Taxonomy

This document describes how the MICCAI index classifies papers, and how the configuration in [`config/taxonomy.yaml`](../config/taxonomy.yaml) and [`config/conference.yaml`](../config/conference.yaml) is interpreted.

The taxonomy is split into four independent dimensions:

| Dimension | Purpose | Source config block |
|---|---|---|
| Tasks | What the paper is trying to accomplish. | `tasks` in `taxonomy.yaml` |
| Modalities | What imaging modality the paper operates on. | `modalities` |
| Methods | Algorithmic family. | `methods` |
| Datasets | Mentioned dataset names. | `datasets` |

A paper may receive multiple labels per dimension (multi-label) and is independently evaluated on each dimension.

## Conference detection

Conference affiliation is established through the **structured evidence model** in `conference_evidence`. A paper receives zero or more evidence records; the strongest evidence determines whether it is in scope.

| Level | Meaning | Example pattern |
|---|---|---|
| `EXPLICIT_STRONG` | Direct acceptance / publication statement. | `accepted to MICCAI`, `camera-ready`, `to appear in MICCAI` |
| `EXPLICIT` | Clear year-marked mention. | `MICCAI 2026`, `MICCAI '26` |
| `INFERRED` | MICCAI mentioned, no year. | `MICCAI` |
| `WEAK` | Submission wording only. | `submitted to MICCAI`, `under review` |

The scope's minimum evidence is configurable:

```yaml
conference_evidence:
  scope_minimum:
    miccai-2026: INFERRED
    miccai-all-years: INFERRED
```

For the strict 2026 scope, an additional check requires the year `2026` (or short form `'26`) to appear somewhere in the paper text — *or* the arXiv ID year to be 26.

## Track detection

Tracks are detected from textual evidence and recorded as one of:

| Track | Evidence patterns |
|---|---|
| `main` | (default when no challenge/workshop wording is found) |
| `workshop` | `\bworkshop\b` |
| `challenge` | `\bchallenge\b`, `\bgrand challenge\b`, `\bcompetition\b` |
| `tutorial` | `\btutorial\b` |
| `dataset` | (assigned manually by a maintainer when appropriate) |
| `unknown` | no evidence |

## Classification algorithm

For each dimension, every label has:

* A `threshold` (minimum weighted evidence required).
* A list of `(regex, weight)` rules.

For a paper `(title, abstract)`:

1. For each label, evaluate every rule against `title` and `abstract`.
2. Title hits contribute `weight × title_multiplier` (default 2). Abstract hits contribute `weight × 1`.
3. Accumulate per-label score.
4. If `score ≥ threshold`, the label is assigned with `confidence = min(1.0, score / (2 × threshold))`.
5. If no label is assigned, the paper is given the synthetic `General` label with confidence 0.1.

This is intentionally simple and deterministic. There is no model dependency.

## Modifying the taxonomy

To add a label:

1. Add an entry to `config/taxonomy.yaml` under the appropriate dimension (`tasks`, `modalities`, `methods`, or `datasets`).
2. Provide at least one rule with a non-zero weight.
3. Set a sensible `threshold` (usually 2).
4. Run `make test` — the unit tests will exercise your change.
5. Run `make build` locally to inspect `dist/modalities.json` (or the appropriate file) and confirm reasonable distribution.

To remove or rename a label:

* Update the YAML.
* Add a migration note to [`DATA_MODEL.md`](./DATA_MODEL.md) if the change is not backwards-compatible.

## Why rule-based and not LLM-based?

This project deliberately avoids a paid-LLM dependency. The reasoning:

* **Determinism** — given the same input, we always produce the same output. An LLM classifier would be stochastic.
* **Provenance** — every assignment is traceable to specific rules and weights. An LLM classifier would be opaque.
* **Cost** — the project runs daily. Even small per-paper LLM calls would dominate cost.
* **Reproducibility** — contributors without API keys can regenerate artifacts.

The taxonomy is *compatible* with adding an optional semantic layer in the future (e.g., sentence embeddings), but the rule-based layer remains the canonical ground truth.

## Coverage and gaps

The current taxonomy covers the most common MICCAI topics, but it is not exhaustive. To suggest additions:

1. Open an issue with concrete paper examples (arXiv IDs) that should match the proposed label.
2. Propose 2-3 example regex rules with weights.
3. Maintainers will evaluate and merge.

Be conservative: high-quality, high-precision labels are more valuable than high-recall labels with false positives.
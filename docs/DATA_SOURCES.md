# Data Sources

This document describes the external data sources used by the MICCAI index pipeline.

## arXiv

* **Purpose**: primary source for paper metadata (title, abstract, comment, authors, primary category, published/updated timestamps).
* **Endpoint**: `http://export.arxiv.org/api/query`
* **Library**: [`arxiv`](https://pypi.org/project/arxiv/) (uses `feedparser` under the hood).
* **Queries**: configured in `config/sources.yaml` under `sources[arxiv].default_queries`.
* **Rate limit**: 30 requests/minute. The source adapter enforces a delay derived from this rate.
* **Retries**: 3 with exponential backoff (factor 2).
* **Cache**: every request is content-hash-keyed and cached for 24 hours by default (configurable in `config/sources.yaml`).

### Why arXiv first?

arXiv is the canonical open-access repository for MICCAI preprints and the most reliable single signal for *recent* MICCAI submissions. Authors almost universally post accepted papers to arXiv shortly after acceptance, and the arXiv `comment` field is the most reliable place to find a "Accepted to MICCAI" line.

### Limitations of arXiv

* arXiv does not contain the official conference DOI/ACM metadata. We do not currently enrich with Crossref/OpenAlex (see [Future Roadmap](#future-roadmap)).
* arXiv search is text-based; classification quality depends on how authors describe their work in title/abstract/comment.
* arXiv metadata can lag the actual submission by days.

## Future roadmap

In priority order:

1. **Crossref enrichment** — fetch canonical DOIs and citation metadata for accepted papers.
2. **OpenAlex enrichment** — additional citation graph and concept tagging.
3. **GitHub/GitLab/HuggingFace verification** — periodically HEAD-check repositories and record `verification.status` (`reachable`, `redirected`, `archived`, `not_found`).
4. **Semantic Scholar** — citation counts and influential-citation signal. *Will not* be used as a paper-quality score.
5. **Conference proceedings import** — when MICCAI publishes its official proceedings (Springer LNCS), we may import the canonical author list and abstracts as a higher-priority source than arXiv.

Any new source must be added behind a config flag (`enabled: bool`), a network-policy block, and a test that runs the source adapter against mocked responses. Do not silently add a new upstream dependency.
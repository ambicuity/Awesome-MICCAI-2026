# Security Policy

## Supported Versions

This project is actively maintained. Security fixes are applied to the `main` branch and released as soon as possible.

## Reporting a Vulnerability

**Please do not file a public issue for security vulnerabilities.**

Email security concerns to the maintainer directly. We aim to acknowledge within 2 business days.

When reporting, please include:

* Description of the issue.
* Reproduction steps.
* Potential impact.
* Suggested fix (if any).

## Security Posture

### GitHub Actions

* Workflows use `permissions: contents: read` by default. PR-opening workflows explicitly request `contents: write` for the duration of the PR.
* We pin actions to major versions (`@v4`, `@v5`, `@v6`) and audit upgrades.
* Concurrency groups prevent redundant runs.
* No `pull_request_target` triggers are used (which would execute untrusted code with write permissions).

### Inputs

* All external data (arXiv metadata, repository URLs) is treated as untrusted.
* The pipeline never executes fetched code, never follows shell expansions in titles/comments, and never renders fetched content as code blocks without escaping.
* The legacy `validate_readme.py` reads README content but only inspects structural markers and URLs — it does not execute any embedded code.

### Dependencies

* The runtime dependency surface is `arxiv` and its transitive dependencies (`feedparser`, `requests`, etc.).
* We deliberately do not add LLM clients, code-execution sandboxes, or untrusted-input parsers.
* CI runs the test suite on every PR; supply-chain attacks that affect tests are caught early.

### Output

* Generated Markdown never embeds raw HTML.
* JSON Schema validation rejects untrusted record shapes before they are persisted.
* The build log is committed to PRs for forensic review, but contains no secrets (no API keys, tokens, or credentials are required by the pipeline).

## Best Practices for Contributors

* Never commit API keys, tokens, or credentials to the repository.
* If you discover that a secret has been committed, contact the maintainer immediately; we will rotate and force-push a clean history.
* When adding a new dependency, prefer packages with active maintenance and minimal transitive surfaces.
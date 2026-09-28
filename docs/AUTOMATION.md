# Automation

This document describes the GitHub Actions workflows that drive the daily MICCAI index update and PR validation.

## Workflows

| Workflow | File | Triggers | Permissions |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | pull_request, manual | `contents: read` |
| Update Data | `.github/workflows/update-data.yml` | daily cron, manual | `contents: read` |

The legacy `update_readme.yml` workflow has been replaced by `update-data.yml` and is no longer the source of truth. It may remain in the repository history but is not invoked.

### CI

Runs on every pull request to `main`:

1. **test** — runs the full test suite (`make test`).
2. **validate** — runs schema validation offline; verifies the existing `README.md` is well-formed against the legacy marker contract.

CI uses the principle of least privilege: the `GITHUB_TOKEN` has `contents: read` only.

### Update Data

Runs daily at 08:00 UTC and on manual dispatch:

1. **build** — runs `python -m miccai_index build --scope miccai-all-years --mode broad --tracks all`.
2. **summary** — writes aggregate statistics to the GitHub Actions job summary.
3. **PR** — if the build succeeds, opens a PR with the diff of `data/`, `dist/`, `README.md`, and the build log.

The workflow **never** force-pushes directly to `main`. All changes go through review.

## Concurrency control

Both workflows use GitHub's `concurrency` block to cancel superseded runs:

```yaml
concurrency:
  group: <workflow>-${{ github.ref }}
  cancel-in-progress: true
```

This prevents a slow build from queuing behind a fast new one.

## Action pinning

Actions are pinned to major versions (`@v4`, `@v5`, `@v6`). The lock to a specific SHA is intentionally avoided so contributors can audit major-version updates, but the major version is documented here for transparency.

| Action | Pinned version |
|---|---|
| `actions/checkout` | `v4` |
| `actions/setup-python` | `v5` |
| `peter-evans/create-pull-request` | `v6` |
| `stefanzweifel/git-auto-commit-action` | `v5` (legacy, may be removed in favor of explicit PR flow) |

## Secrets

The workflows require only the default `GITHUB_TOKEN` provided by GitHub Actions. **No additional secrets are required** to run the pipeline. The arXiv API is unauthenticated.

## Local reproduction

You should be able to reproduce any CI run locally:

```bash
make setup
make test
make validate-offline
```

If a build is needed locally with network access:

```bash
make build
```

The artifact directory is `dist/`.

## Failure modes and recovery

| Symptom | Likely cause | Recovery |
|---|---|---|
| `CI / validate` fails on a PR | New data product invalid against schema | Fix the producer; the test message will show the exact path and reason. |
| `Update Data / build` fails | arXiv API transient error | The next scheduled run will retry; manual `workflow_dispatch` after the issue is resolved. |
| PR opened but with empty diff | No new papers discovered | Expected behavior; the PR is closed automatically by the workflow (`delete-branch: true`). |
| Coverage dropped unexpectedly | arXiv API restriction or new filter bug | Open an issue; do not push a fix without reproducing locally first. |

## Configuration changes

Workflow changes should follow the same review standards as code changes:

* Open a PR.
* Describe the rationale in the PR description.
* Reference any related issue.
* Wait for review before merging.

Workflows cannot edit their own permissions in a way that broadens them without a separate review.
"""README rendering.

The renderer mutates an existing ``README.md`` template by replacing the
content between marker pairs. The template is the source of truth for the
human-readable layout; markers define the contract between the static prose
and the generated sections.

Marker contract:

* ``<!-- BEGIN COVERAGE_REPORT -->...<!-- END COVERAGE_REPORT -->``
* ``<!-- BEGIN <CATEGORY>_PAPERS -->...<!-- END <CATEGORY>_PAPERS -->``
* ``**Conference Scope**: ...``
* ``**Discovery Mode**: ...``
* ``**Last Updated**: ...``
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence

from ..discovery import PaperRecord

README_CATEGORY_ORDER: List[str] = [
    "Segmentation",
    "Reconstruction",
    "Classification",
    "Image Registration",
    "Domain Adaptation",
    "Generative Models",
    "General",
]

CATEGORY_MARKERS = {
    "Segmentation": "SEGMENTATION",
    "Reconstruction": "RECONSTRUCTION",
    "Classification": "CLASSIFICATION",
    "Image Registration": "IMAGE_REGISTRATION",
    "Domain Adaptation": "DOMAIN_ADAPTATION",
    "Generative Models": "GENERATIVE_MODELS",
    "General": "GENERAL",
}

COVERAGE_BLOCK_PATTERN = re.compile(
    r"<!-- BEGIN COVERAGE_REPORT -->(?P<body>.*?)<!-- END COVERAGE_REPORT -->", re.S
)
SCOPE_LINE_PATTERN = re.compile(r"\*\*Conference Scope\*\*: [^\n]*")
MODE_LINE_PATTERN = re.compile(r"\*\*Discovery Mode\*\*: [^\n]*")
LAST_UPDATED_PATTERN = re.compile(r"\*\*Last Updated\*\*: [^\n]*")


def _sort_key(paper: PaperRecord):
    published = paper.identifiers.get("arxiv", {}).get("published", "")
    try:
        ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        ts = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (-ts.timestamp(), paper.title.lower())


def generate_category_markdown(papers: Sequence[PaperRecord], category: str) -> str:
    """Generate the markdown body for one category."""
    selected = [p for p in papers if category in p.categories]
    selected.sort(key=_sort_key)
    lines: List[str] = []
    for paper in selected:
        repos = paper.repositories
        if not repos:
            continue
        primary = repos[0]
        # Prefer the arXiv abstract URL as the canonical title link; fall back
        # to the paper's first repository URL when arXiv metadata is missing.
        arxiv_url = paper.identifiers.get("arxiv", {}).get("url", "") or primary["url"]
        confidence = paper.confidence.get("tasks", {}).get(_task_id_for_label(category))
        if confidence is None:
            confidence_label = (
                "high" if paper.confidence.get("overall", 0) >= 0.6 else "medium"
            )
        else:
            confidence_label = "high" if confidence >= 0.6 else "medium"
        extras = ""
        if len(repos) > 1:
            extras = " | " + " | ".join(
                f"[Code{i + 2}]({r['url']})" for i, r in enumerate(repos[1:])
            )
        lines.append(
            f"* **[{paper.title}]({arxiv_url})** - "
            f"[Code]({primary['url']}) (confidence: {confidence_label}){extras}"
        )
    return "\n".join(lines)


_TASK_ID_FOR_LABEL = {
    "Segmentation": "segmentation",
    "Reconstruction": "reconstruction",
    "Classification": "classification",
    "Image Registration": "registration",
    "Domain Adaptation": "domain_adaptation",
    "Generative Models": "generative_models",
}


def _task_id_for_label(label: str) -> str:
    return _TASK_ID_FOR_LABEL.get(label, label.lower())


def build_coverage_report(
    papers: Sequence[PaperRecord],
    stats: Dict[str, int],
    conference_scope: str,
    mode: str,
    tracks: str,
) -> str:
    counts = {cat: 0 for cat in README_CATEGORY_ORDER}
    for paper in papers:
        for cat in paper.categories:
            if cat in counts:
                counts[cat] += 1
    total = sum(counts.values())
    lines = [
        f"- Conference scope: `{conference_scope}`",
        f"- Discovery mode: `{mode}`",
        f"- Tracks: `{tracks}`",
        f"- Total code-backed papers: `{total}`",
        f"- Fetched arXiv records: `{stats.get('fetched_records', 0)}`",
        f"- Unique arXiv records: `{stats.get('unique_records', 0)}`",
        f"- Filtered (non-target): `{stats.get('filtered_non_target', 0)}`",
        f"- Filtered (track): `{stats.get('filtered_track', 0)}`",
        f"- Filtered (no code links): `{stats.get('filtered_no_code', 0)}`",
        f"- Uncertain taxonomy papers: `{stats.get('uncertain_records', 0)}`",
        "",
        "| Category | Count | Gap to 1000 |",
        "|---|---:|---:|",
    ]
    for category in README_CATEGORY_ORDER:
        count = counts[category]
        gap = max(0, 1000 - count)
        lines.append(f"| {category} | {count} | {gap} |")
    return "\n".join(lines)


def replace_marker_block(content: str, marker: str, body: str) -> str:
    pattern = rf"(<!-- BEGIN {marker}_PAPERS -->).*?(<!-- END {marker}_PAPERS -->)"
    if not re.search(pattern, content, flags=re.DOTALL):
        raise ValueError(f"Missing marker block for {marker}")
    replacement = f"\\1\n{body}\n\\2" if body else f"\\1\n\\2"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)


def render_readme(
    papers: Sequence[PaperRecord],
    stats: Dict[str, int],
    conference_scope: str,
    mode: str,
    tracks: str,
    readme_text: str,
    timestamp: str | None = None,
) -> str:
    """Apply generated sections to an existing README template."""
    content = readme_text
    category_counts: Dict[str, int] = {}
    for category in README_CATEGORY_ORDER:
        marker = CATEGORY_MARKERS[category]
        body = generate_category_markdown(papers, category)
        content = replace_marker_block(content, marker, body)
        category_counts[category] = sum(
            1 for p in papers if category in p.categories
        )

    coverage_body = build_coverage_report(
        papers, stats, conference_scope, mode, tracks
    )
    if COVERAGE_BLOCK_PATTERN.search(content):
        content = COVERAGE_BLOCK_PATTERN.sub(
            f"<!-- BEGIN COVERAGE_REPORT -->\n{coverage_body}\n<!-- END COVERAGE_REPORT -->",
            content,
        )

    content = SCOPE_LINE_PATTERN.sub(
        f"**Conference Scope**: {conference_scope}", content
    )
    content = MODE_LINE_PATTERN.sub(f"**Discovery Mode**: {mode}", content)

    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = LAST_UPDATED_PATTERN.sub(
        f"**Last Updated**: {timestamp} by GitHub Actions", content
    )
    return content


def update_readme_markers(
    readme_path: str,
    papers: Sequence[PaperRecord],
    stats: Dict[str, int],
    conference_scope: str,
    mode: str,
    tracks: str,
) -> Dict[str, int]:
    """Convenience: read ``readme_path``, apply markers, write back."""
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = render_readme(papers, stats, conference_scope, mode, tracks, content)
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    counts: Dict[str, int] = {}
    for cat in README_CATEGORY_ORDER:
        counts[cat] = sum(1 for p in papers if cat in p.categories)
    return counts
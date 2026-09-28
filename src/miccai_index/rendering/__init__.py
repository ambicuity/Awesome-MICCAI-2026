"""Rendering layer — produce README, data products, and reports."""

from .data_products import (
    build_dist_products,
    write_dist_products,
)
from .readme import (
    README_CATEGORY_ORDER,
    render_readme,
    update_readme_markers,
)

__all__ = [
    "README_CATEGORY_ORDER",
    "render_readme",
    "update_readme_markers",
    "build_dist_products",
    "write_dist_products",
]
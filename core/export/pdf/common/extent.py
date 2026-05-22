"""Compatibility wrapper for extent utilities.

The real implementations reside in ``core/export/pdf/common/layout/extent.py``.
This module re‑exports the symbols to keep existing import paths functional.
"""

from .layout.extent import compute_export_extent, get_source_vector_layer  # noqa: F401

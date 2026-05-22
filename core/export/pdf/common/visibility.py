"""Compatibility wrapper for visibility utilities.

The real implementation is now located in ``core/export/pdf/common/layout/visibility.py``.
Exports are re‑exported here for backward‑compatible imports.
"""

from .layout.visibility import temporary_visible_layers  # noqa: F401

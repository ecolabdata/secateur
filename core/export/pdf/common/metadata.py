"""Compatibility wrapper for metadata utilities.

The actual implementations now reside in ``core/export/pdf/common/layout/metadata.py``.
This module re-exports the symbols to preserve existing import paths.
"""

from .layout.metadata import apply_label_text, apply_logo, inject_basic_metadata  # noqa: F401

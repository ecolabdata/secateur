"""
Layout items utility for GeoPDF export.

This module provides helper functions for handling layout items in GeoPDF exports.
"""

from typing import List, Optional

from qgis.core import QgsLayoutItem, QgsPrintLayout


def get_layout_item(layout: QgsPrintLayout, item_id: str) -> QgsLayoutItem:
    """Get a layout item by its ID, raising an error if not found."""
    item = layout.itemById(item_id)

    if item is None:
        raise ValueError(f"Layout item '{item_id}' not found")

    return item
"""
Common layout items utilities for PDF export.
"""

from qgis.core import QgsLayout, QgsLayoutItem


def get_required_item[T: QgsLayoutItem](
    layout: QgsLayout,
    item_id: str,
    expected_type: type[T],
) -> T:
    """Get a required layout item by ID with type checking."""
    item = layout.itemById(item_id)
    if item is None:
        raise ValueError(f"Layout item '{item_id}' not found")
    if not isinstance(item, expected_type):
        raise TypeError(f"Layout item '{item_id}' is not a {expected_type.__name__}, got {type(item).__name__}")
    return item


def get_optional_item[T: QgsLayoutItem](
    layout: QgsLayout,
    item_id: str,
    expected_type: type[T],
) -> T | None:
    """Get an optional layout item by ID with type checking."""
    item = layout.itemById(item_id)
    if item is None:
        return None
    if not isinstance(item, expected_type):
        raise TypeError(f"Layout item '{item_id}' is not a {expected_type.__name__}, got {type(item).__name__}")
    return item

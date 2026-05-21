"""
Layout items utility for GeoPDF export.

This module provides helper functions for handling layout items in GeoPDF exports.
"""

from dataclasses import dataclass
from typing import TypeVar

from qgis.core import (
    QgsLayoutItem,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsPrintLayout,
)

T = TypeVar("T", bound=QgsLayoutItem)


@dataclass(slots=True)
class ReportLayoutItems:
    """Container for commonly accessed layout items in a GeoPDF report.

    Attributes:
        map_item: The map frame item (required).
        title_item: Title label item.
        author_item: Author label item.
        date_item: Date label item.
        logo_item: Logo picture item.
    """

    map_item: QgsLayoutItemMap
    title_item: QgsLayoutItemLabel
    author_item: QgsLayoutItemLabel
    date_item: QgsLayoutItemLabel
    logo_item: QgsLayoutItemPicture


def resolve_layout_items(layout: QgsPrintLayout) -> ReportLayoutItems:
    """Retrieve and validate all required layout items from a ``QgsPrintLayout``.

    Raises:
        ValueError: If any required item is missing.
        TypeError: If an item is not of the expected ``QgsLayoutItem`` subclass.
    """

    # Helper to fetch and assert type
    def _get_item(
        item_id: str,
        expected_type: type[T],
    ) -> T:
        item = layout.itemById(item_id)
        if item is None:
            raise ValueError(f"Layout item '{item_id}' not found")
        if not isinstance(item, expected_type):
            raise TypeError(f"Layout item '{item_id}' is not a {expected_type.__name__}, got {type(item).__name__}")
        return item

    map_item = _get_item("Map 1", QgsLayoutItemMap)
    title_item = _get_item("title", QgsLayoutItemLabel)
    author_item = _get_item("author", QgsLayoutItemLabel)
    date_item = _get_item("date", QgsLayoutItemLabel)
    logo_item = _get_item("logo", QgsLayoutItemPicture)

    return ReportLayoutItems(
        map_item=map_item,
        title_item=title_item,
        author_item=author_item,
        date_item=date_item,
        logo_item=logo_item,
    )

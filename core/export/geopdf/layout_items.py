"""
Layout items utility for GeoPDF export.

This module provides helper functions for handling layout items in GeoPDF exports.
"""

from qgis.core import QgsPrintLayout

from ...export.pdf.common.layout_items import get_required_item


def resolve_layout_items(layout: QgsPrintLayout):
    """Retrieve and validate all required layout items from a ``QgsPrintLayout``.

    Raises:
        ValueError: If any required item is missing.
        TypeError: If an item is not of the expected ``QgsLayoutItem`` subclass.
    """
    # Import here to avoid circular imports
    from qgis.core import (
        QgsLayoutItemLabel,
        QgsLayoutItemMap,
        QgsLayoutItemPicture,
    )

    map_item = get_required_item(layout, "Map 1", QgsLayoutItemMap)
    title_item = get_required_item(layout, "title", QgsLayoutItemLabel)
    author_item = get_required_item(layout, "author", QgsLayoutItemLabel)
    date_item = get_required_item(layout, "date", QgsLayoutItemLabel)
    logo_item = get_required_item(layout, "logo", QgsLayoutItemPicture)

    # Create a simple namespace-like object to represent the layout items
    class ReportLayoutItems:
        def __init__(self, map_item, title_item, author_item, date_item, logo_item):
            self.map_item = map_item
            self.title_item = title_item
            self.author_item = author_item
            self.date_item = date_item
            self.logo_item = logo_item

    return ReportLayoutItems(map_item, title_item, author_item, date_item, logo_item)

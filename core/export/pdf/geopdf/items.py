from dataclasses import dataclass

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsPrintLayout,
)

from ..common.layout.items import get_required_item


@dataclass(slots=True)
class GeoPdfLayoutItems:
    """Typed container for required layout items in a GeoPDF export."""

    map_item: QgsLayoutItemMap
    title_item: QgsLayoutItemLabel
    author_item: QgsLayoutItemLabel
    date_item: QgsLayoutItemLabel
    logo_item: QgsLayoutItemPicture


def resolve_layout_items(layout: QgsPrintLayout) -> GeoPdfLayoutItems:
    """Retrieve and validate required layout items, returning a typed container."""
    map_item = get_required_item(layout, "Map 1", QgsLayoutItemMap)
    title_item = get_required_item(layout, "title", QgsLayoutItemLabel)
    author_item = get_required_item(layout, "author", QgsLayoutItemLabel)
    date_item = get_required_item(layout, "date", QgsLayoutItemLabel)
    logo_item = get_required_item(layout, "logo", QgsLayoutItemPicture)
    return GeoPdfLayoutItems(
        map_item=map_item,
        title_item=title_item,
        author_item=author_item,
        date_item=date_item,
        logo_item=logo_item,
    )

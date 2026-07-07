from dataclasses import dataclass
from typing import TYPE_CHECKING

from qgis.core import (
    QgsLayout,
    QgsLayoutItemLabel,
    QgsLayoutItemPicture,
)

if TYPE_CHECKING:
    from .metadata import MetadataLayoutItems


@dataclass(slots=True)
class MetadataLayoutItems:
    """Bundle of the optional metadata layout items shared by all PDF layouts."""

    title_item: QgsLayoutItemLabel | None
    author_item: QgsLayoutItemLabel | None
    date_item: QgsLayoutItemLabel | None
    logo_item: QgsLayoutItemPicture | None


def get_metadata_layout_items(
    layout: QgsLayout,
    get_optional_item_func,
    get_required_item_func,
) -> MetadataLayoutItems:
    """Extract standard metadata layout items from a layout."""
    return MetadataLayoutItems(
        title_item=get_optional_item_func(
            layout,
            "title",
            QgsLayoutItemLabel,
        ),
        author_item=get_optional_item_func(
            layout,
            "author",
            QgsLayoutItemLabel,
        ),
        date_item=get_optional_item_func(
            layout,
            "date",
            QgsLayoutItemLabel,
        ),
        logo_item=get_optional_item_func(
            layout,
            "logo",
            QgsLayoutItemPicture,
        ),
    )

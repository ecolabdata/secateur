from dataclasses import dataclass

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
)

from ..common.layout.metadata_items import MetadataLayoutItems


@dataclass(slots=True)
class MultiPdfLayoutItems(
    MetadataLayoutItems,
):
    map_item: QgsLayoutItemMap

    page_item: QgsLayoutItemLabel | None

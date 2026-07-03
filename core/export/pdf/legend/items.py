from dataclasses import dataclass

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
)

from ..common.layout.metadata_items import MetadataLayoutItems


@dataclass(slots=True)
class LegendLayoutItems(
    MetadataLayoutItems,
):
    legend: QgsLayoutItemLegend

    page_item: QgsLayoutItemLabel | None

from dataclasses import dataclass

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsPrintLayout,
)

from ..common.layout.items import (
    get_optional_item,
    get_required_item,
)


@dataclass(slots=True)
class LegendLayoutItems:
    legend: QgsLayoutItemLegend

    title_item: QgsLayoutItemLabel | None
    author_item: QgsLayoutItemLabel | None
    date_item: QgsLayoutItemLabel | None

    logo_item: QgsLayoutItemPicture | None

    page_item: QgsLayoutItemLabel | None


def resolve_layout_items(
    layout: QgsPrintLayout,
) -> LegendLayoutItems:
    return LegendLayoutItems(
        legend=get_required_item(
            layout,
            "legend",
            QgsLayoutItemLegend,
        ),
        title_item=get_optional_item(
            layout,
            "title",
            QgsLayoutItemLabel,
        ),
        author_item=get_optional_item(
            layout,
            "author",
            QgsLayoutItemLabel,
        ),
        date_item=get_optional_item(
            layout,
            "date",
            QgsLayoutItemLabel,
        ),
        logo_item=get_optional_item(
            layout,
            "logo",
            QgsLayoutItemPicture,
        ),
        page_item=get_optional_item(
            layout,
            "page",
            QgsLayoutItemLabel,
        ),
    )

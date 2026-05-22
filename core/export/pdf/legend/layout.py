import textwrap
from pathlib import Path

from qgis.core import (
    QgsLayerTree,
    QgsLayoutItemLegend,
    QgsPrintLayout,
    QgsProject,
)

from ....utils.formatting import display_date_str
from ..common.layout.metadata import inject_basic_metadata
from ..common.template_loader import create_layout_from_template
from .items import (
    LegendLayoutItems,
    resolve_layout_items,
)


def _build_legend_tree(
    project: QgsProject,
    layer_names: list[str],
) -> QgsLayerTree:
    root = QgsLayerTree()
    root.setName("LegendRoot")

    for layer_name in layer_names:
        layers = project.mapLayersByName(layer_name)
        if not layers:
            continue
        layer = layers[0]
        node = root.addLayer(layer)
        wrapped_name = "\n".join(textwrap.wrap(node.name(), width=100))
        node.setName(wrapped_name)
    return root


def _configure_legend(
    legend: QgsLayoutItemLegend,
    root: QgsLayerTree,
) -> None:
    legend.setAutoUpdateModel(False)
    legend.model().setRootGroup(root)
    legend.invalidateCache()
    legend.updateLegend()
    legend.refresh()
    legend.adjustBoxSize()


def _populate_metadata(
    items: LegendLayoutItems,
    *,
    title: str,
    author: str,
    logo_path: Path | None,
    page_number: int,
    total_pages: int,
) -> None:
    from ..common.models import LayoutMetadata

    inject_basic_metadata(
        title_item=items.title_item,
        author_item=items.author_item,
        date_item=items.date_item,
        logo_item=items.logo_item,
        metadata=LayoutMetadata(
            title=title,
            author=author,
            date_text=display_date_str(),
            logo_path=logo_path,
        ),
    )
    if items.page_item:
        items.page_item.setText(f"{page_number}/{total_pages}")
        items.page_item.refresh()


def build_legend_layout(
    *,
    project: QgsProject,
    template_path: Path,
    layer_names: list[str],
    title: str,
    author: str,
    logo_path: Path | None,
    page_number: int,
    total_pages: int,
) -> QgsPrintLayout:
    layout = create_layout_from_template(
        project=project,
        template_path=template_path,
        layout_name=f"Legend_{page_number}",
        register_in_manager=False,
    )

    items = resolve_layout_items(layout)

    root = _build_legend_tree(
        project,
        layer_names,
    )

    _configure_legend(
        items.legend,
        root,
    )

    _populate_metadata(
        items,
        title=title,
        author=author,
        logo_path=logo_path,
        page_number=page_number,
        total_pages=total_pages,
    )

    layout.refresh()
    return layout

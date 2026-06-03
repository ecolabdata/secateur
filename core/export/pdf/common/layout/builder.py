"""
Common layout builder shared between GeoPDF and Multi‑page PDF exporters.
"""

from pathlib import Path

from qgis.core import (
    QgsLayout,
    QgsLayoutItemMap,
    QgsMapLayer,
    QgsProject,
    QgsRectangle,
)

from ..lifecycle.refresh import stabilize_layout
from ..template_loader import create_layout_from_template
from .metadata import apply_label_text, apply_logo

# Optional import for GeoPDF‑specific map configuration. Imported lazily to avoid
# circular dependencies when the builder is used by the multi‑page exporter.


def _configure_geopdf_map(
    map_item: QgsLayoutItemMap,
    extent_rect: QgsRectangle,
    result_layers: list[QgsMapLayer],
    basemap_layer: QgsMapLayer | None,
) -> None:
    from ...geopdf.layout import configure_layout_map  # type: ignore

    configure_layout_map(
        map_item=map_item,
        extent_rect=extent_rect,
        result_layers=result_layers,
        basemap_layer=basemap_layer,
    )


def build_layout_from_template(
    *,
    project: QgsProject,
    template_path: Path,
    layout_name: str,
    title: str,
    author: str,
    date_text: str | None = None,
    logo_path: str | Path | None = None,
    extent_rect: QgsRectangle | None = None,
    result_layers: list[QgsMapLayer] | None = None,
    basemap_layer: QgsMapLayer | None = None,
    visible_layers: list[QgsMapLayer] | None = None,
) -> QgsLayout:
    """Create a layout from a QPT template and populate common elements.

    The function centralises the steps that are identical for the GeoPDF and
    multi‑page PDF exporters:

    * Load the template.
    * Populate title, author, date and optional logo.
    * Optionally configure the map item (either via the GeoPDF helper or a
      simple layer list).
    * Stabilise the layout before returning.
    """
    layout = create_layout_from_template(
        project=project,
        template_path=template_path,
        layout_name=layout_name,
        register_in_manager=False,
    )

    # Populate metadata items – layout IDs are shared across exporters.
    title_item = layout.itemById("title")
    apply_label_text(title_item, title)

    author_item = layout.itemById("author")
    apply_label_text(author_item, author)

    if date_text is not None:
        date_item = layout.itemById("date")
        apply_label_text(date_item, date_text)

    if logo_path:
        logo_item = layout.itemById("logo")
        apply_logo(logo_item, Path(logo_path))

    # Map configuration – the caller can provide either the GeoPDF‑style
    # arguments (extent + result_layers) or the simpler visible_layers list.
    map_item = layout.itemById("Map 1")
    if map_item and extent_rect:
        if result_layers is not None:
            # GeoPDF workflow – keep basemap order.
            _configure_geopdf_map(
                map_item=map_item,
                extent_rect=extent_rect,
                result_layers=result_layers,
                basemap_layer=basemap_layer,
            )
        elif visible_layers is not None:
            # Multi‑page PDF workflow.
            map_item.zoomToExtent(extent_rect)
            map_item.setLayers(visible_layers)
            map_item.setKeepLayerSet(True)

    stabilize_layout(layout)
    return layout

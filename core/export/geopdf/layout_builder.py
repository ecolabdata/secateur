"""
Layout building utilities for GeoPDF export.

This module provides functions for building and configuring the print layout
for GeoPDF exports, separated from the main service logic.
"""

import os
from contextlib import contextmanager
from typing import List, Optional
from...utils.formatting import timestamp_str

from qgis.core import (
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument

from...logger import logger
from...utils.layouts import clean_layouts
from...utils.rendering import is_simple_fill, set_layer_opacity
from...utils.visibility import clear_all_visibility, set_layer_and_parents_visible
from .extent import compute_export_extent, get_source_vector_layer


def resolve_output_path(output_path: str) -> tuple[str, str]:
    """Resolve the final PDF path and a timestamp string.

    If *output_path* is a directory, a filename ``Rapport_cartographique_<timestamp>.pdf``
    is created inside it. Otherwise *output_path* is returned unchanged.
    """
    try:
        if os.path.isdir(output_path):
            from...utils.formatting import timestamp_str
            date_hm = timestamp_str()
            filename = f"Rapport_cartographique_{date_hm}.pdf"
            full_path = os.path.join(output_path, filename)
        else:
            full_path = output_path
            from...utils.formatting import timestamp_str
            date_hm = timestamp_str()
        return full_path, date_hm
    except Exception as e:
        logger.error(f"Failed to resolve output path '{output_path}': {e}")
        raise

@contextmanager
def temporary_visible_layers(
    root, result_layers: List[QgsMapLayer], basemap_layer: QgsMapLayer | None
):
    """Temporarily hide all layers then make *result_layers* (and optional *basemap_layer*) visible.

    Yields the list of layer names used for the legend.
    """
    visible_count = 0
    # Hide everything via the existing ``clear_all_visibility`` helper
    with clear_all_visibility(root):

        def _make_visible(layer):
            nonlocal visible_count
            try:
                if is_simple_fill(layer):
                    set_layer_opacity(layer, opacity=0.8)
                visible_count += int(set_layer_and_parents_visible(root, layer))
            except Exception as exc:
                logger.exception("Could not set visibility for layer %s: %s", layer.name(), exc)

        for layer in result_layers:
            _make_visible(layer)
        if visible_count == 0:
            logger.warning("temporary_visible_layers: no result layers could be made visible")
        if basemap_layer is not None:
            try:
                visible_count += int(set_layer_and_parents_visible(root, basemap_layer))
            except Exception as exc:
                logger.exception("Could not set visibility for basemap layer %s: %s", basemap_layer.name(), exc)
        layer_names = [lyr.name() for lyr in result_layers]
        yield layer_names


def load_layout_from_template(
    project: QgsProject,
    manager,
    template_path: str,
    layout_name: str,
) -> QgsPrintLayout:
    """Load a layout from a QPT template file."""
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)

    with open(template_path, encoding="utf-8") as f:
        template_content = f.read()

    doc = QDomDocument()
    success, error_message, error_line, error_column = doc.setContent(template_content)

    if not success:
        raise ValueError(f"Failed to parse QPT template (line={error_line}, column={error_column}): {error_message}")

    context = QgsReadWriteContext()

    items, ok = layout.loadFromTemplate(doc, context)

    if not ok:
        raise RuntimeError(f"Failed to load layout template: {template_path}")

    manager.addLayout(layout)

    return layout


def get_layout_item(layout: QgsPrintLayout, item_id: str):
    """Get a layout item by its ID, raising an error if not found."""
    item = layout.itemById(item_id)

    if item is None:
        raise ValueError(f"Layout item '{item_id}' not found")

    return item


def configure_layout_map(
    layout: QgsPrintLayout,
    extent_rect: QgsRectangle,
) -> None:
    """Configure the map item in the layout from template."""

    map_item = get_layout_item(layout, "Map 1")

    if not isinstance(map_item, QgsLayoutItemMap):
        raise TypeError(f"Layout item 'Map 1' is not a QgsLayoutItemMap, got {type(map_item)}")

    logger.info(
        "Applying export extent to map item: xmin=%s ymin=%s xmax=%s ymax=%s",
        extent_rect.xMinimum(),
        extent_rect.yMinimum(),
        extent_rect.xMaximum(),
        extent_rect.yMaximum(),
    )

    # ------------------------------------------------------------------
    # IMPORTANT:
    # The template map frame has its own aspect ratio.
    # We must adapt the geographic extent to that ratio,
    # otherwise QGIS expands the map unpredictably.
    # ------------------------------------------------------------------

    map_rect = map_item.rect()

    frame_width = map_rect.width()
    frame_height = map_rect.height()

    if frame_height == 0:
        raise ValueError("Map frame height is zero")

    frame_ratio = frame_width / frame_height

    extent_width = extent_rect.width()
    extent_height = extent_rect.height()

    if extent_height == 0:
        raise ValueError("Extent height is zero")

    extent_ratio = extent_width / extent_height

    adjusted_extent = QgsRectangle(extent_rect)

    # ------------------------------------------------------------------
    # Adjust extent to frame aspect ratio
    # ------------------------------------------------------------------

    if extent_ratio > frame_ratio:
        # extent too wide -> increase height
        new_height = extent_width / frame_ratio
        delta = (new_height - extent_height) / 2

        adjusted_extent.setYMinimum(extent_rect.yMinimum() - delta)
        adjusted_extent.setYMaximum(extent_rect.yMaximum() + delta)

    else:
        # extent too tall -> increase width
        new_width = extent_height * frame_ratio
        delta = (new_width - extent_width) / 2

        adjusted_extent.setXMinimum(extent_rect.xMinimum() - delta)
        adjusted_extent.setXMaximum(extent_rect.xMaximum() + delta)

    logger.info(
        "Adjusted extent: xmin=%s ymin=%s xmax=%s ymax=%s",
        adjusted_extent.xMinimum(),
        adjusted_extent.yMinimum(),
        adjusted_extent.xMaximum(),
        adjusted_extent.yMaximum(),
    )

    # ------------------------------------------------------------------
    # Reset inherited template state
    # ------------------------------------------------------------------

    map_item.setAtlasDriven(False)

    # Important with QPT templates
    map_item.setKeepLayerSet(False)
    map_item.setKeepLayerStyles(False)

    # ------------------------------------------------------------------
    # Apply corrected extent
    # ------------------------------------------------------------------

    map_item.zoomToExtent(adjusted_extent)

    # Force redraw
    map_item.refresh()
    map_item.invalidateCache()
    map_item.update()


def populate_layout_texts(
    layout: QgsPrintLayout,
    title: str,
    author: str,
    date_hm: str,
) -> None:
    """Populate text items in the layout with dynamic content."""
    # Title
    title_item = get_layout_item(layout, "title")
    if not isinstance(title_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'title' is not a QgsLayoutItemLabel, got {type(title_item)}")
    title_item.setText(title)
    title_item.refresh()

    # Author
    author_item = get_layout_item(layout, "author")
    if not isinstance(author_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'author' is not a QgsLayoutItemLabel, got {type(author_item)}")
    author_item.setText(author or "")
    author_item.refresh()

    # Date
    date_item = get_layout_item(layout, "date")
    if not isinstance(date_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'date' is not a QgsLayoutItemLabel, got {type(date_item)}")
    date_item.setText(date_hm)
    date_item.refresh()


def populate_layout_logo(
    layout: QgsPrintLayout,
    logo_path: Optional[str],
) -> None:
    """Populate the logo item in the layout with a dynamic logo."""
    logo_item = get_layout_item(layout, "logo")

    if not isinstance(logo_item, QgsLayoutItemPicture):
        raise TypeError(f"Layout item 'logo' is not a QgsLayoutItemPicture, got {type(logo_item)}")

    if logo_path and os.path.exists(logo_path):
        logo_item.setPicturePath(logo_path)
        logo_item.refresh()


def build_report_layout(
    project: QgsProject,
    template_path: str,
    date_hm: Optional[str],
    extent_rect: QgsRectangle,
    logo_path: Optional[str],
    title: str,
    author: str,
    basemap_layer: QgsMapLayer | None,
) -> QgsPrintLayout:
    """Create the layout from a QPT template and populate it with dynamic content.

    Returns the fully prepared ``QgsPrintLayout``.
    """
    manager = project.layoutManager()

    clean_layouts(manager)

    # Ensure we have a timestamp string for layout naming and date field
    if date_hm is None:
        date_hm = timestamp_str()
    layout_name = f"GeoPDF_{date_hm}"

    layout = load_layout_from_template(
        project=project,
        manager=manager,
        template_path=template_path,
        layout_name=layout_name,
    )

    configure_layout_map(
        layout=layout,
        extent_rect=extent_rect,
    )

    # Refresh layout to ensure map changes are applied
    layout.refresh()

    populate_layout_texts(
        layout=layout,
        title=title,
        author=author,
        date_hm=date_hm,
    )

    populate_layout_logo(
        layout=layout,
        logo_path=logo_path,
    )

    layout.refresh()

    return layout
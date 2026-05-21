"""
Layout building utilities for GeoPDF export.

This module provides functions for building and configuring the print layout
for GeoPDF exports, separated from the main service logic.
"""

import os

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsRectangle,
)
from qgis.PyQt.QtXml import QDomDocument

from ...logger import logger
from ...utils.formatting import timestamp_str
from ...utils.layouts import clean_layouts, get_layout_item


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
    logo_path: str | None,
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
    date_hm: str | None,
    extent_rect: QgsRectangle,
    logo_path: str | None,
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

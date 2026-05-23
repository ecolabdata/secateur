"""
Unified layout utilities for GeoPDF export.

This module consolidates layout building, map configuration, and item population
functions that were previously split across several files. It provides a simple
API for constructing a QGIS print layout ready for GeoPDF export.
"""

from pathlib import Path

from qgis.core import (
    QgsLayoutItemMap,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
)

from ....logger import logger
from ..common.layout.metadata import apply_label_text, apply_logo
from ..common.template_loader import create_layout_from_template as load_layout_from_template
from .items import resolve_layout_items


def populate_layout_texts(items, title: str, author: str, date_hm: str) -> None:
    """Populate title, author and date label items.

    The function validates each item type before setting the text.
    """
    apply_label_text(items.title_item, title)
    apply_label_text(items.author_item, author or "")
    apply_label_text(items.date_item, date_hm)


def populate_layout_logo(items, logo_path: str | None) -> None:
    """Set the logo picture item if a valid path is provided.

    If ``logo_path`` is ``None`` or does not exist on the filesystem, the logo
    item remains unchanged.
    """
    import os

    if logo_path and os.path.exists(logo_path):
        apply_logo(items.logo_item, Path(logo_path))


def build_report_layout(
    project: QgsProject,
    template_path: str,
    date_hm: str | None,
    extent_rect: QgsRectangle,
    logo_path: str | None,
    title: str,
    author: str,
) -> QgsPrintLayout:
    """Construct a QgsPrintLayout ready for GeoPDF export.

    The function loads the QPT template, configures the map extent, injects
    metadata texts and an optional logo.
    """
    # Load template and obtain a fresh layout instance
    layout_name = "GeoPDF"
    layout = load_layout_from_template(
        project=project,
        template_path=Path(template_path),
        layout_name=layout_name,
        register_in_manager=False,
    )

    # Resolve layout items
    items = resolve_layout_items(layout)
    # Configure map geometry
    configure_layout_map(map_item=items.map_item, extent_rect=extent_rect)
    from ..common.lifecycle.refresh import stabilize_layout

    stabilize_layout(layout)

    # Populate dynamic text fields
    populate_layout_texts(items, title=title, author=author, date_hm=date_hm or "")
    # Populate optional logo
    populate_layout_logo(items, logo_path=logo_path)
    from ..common.lifecycle.refresh import stabilize_layout

    stabilize_layout(layout)
    return layout


def configure_layout_map(map_item: QgsLayoutItemMap, extent_rect: QgsRectangle) -> None:
    """Configure the map item in the layout from template.

    Adjusts the geographic extent to match the aspect ratio of the map frame
    defined in the QPT template, applying the corrected extent to the map item.
    """
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

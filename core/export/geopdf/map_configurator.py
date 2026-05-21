"""
Map configurator utilities for GeoPDF export.
"""

import logging
from qgis.core import QgsPrintLayout, QgsRectangle, QgsLayoutItemMap

from ...utils.layouts import get_layout_item
from ...logger import logger


def configure_layout_map(layout: QgsPrintLayout, extent_rect: QgsRectangle) -> None:
    """Configure the map item in the layout from template.

    Adjusts the geographic extent to match the aspect ratio of the map frame
    defined in the QPT template, applying the corrected extent to the map item.
    """
    map_item = get_layout_item(layout, "Map 1")

    if not isinstance(map_item, QgsLayoutItemMap):
        raise TypeError(
            f"Layout item 'Map 1' is not a QgsLayoutItemMap, got {type(map_item)}"
        )

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

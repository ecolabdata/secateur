"""
Centralized layout stabilization utilities.
Ensures all layout items are refreshed safely for QGIS 3.34.
"""

from contextlib import suppress

from qgis.core import (
    QgsLayout,
    QgsLayoutItemLegend,
)
from qgis.PyQt.QtWidgets import QApplication


def _refresh_item(item) -> None:
    """Refresh a single layout item according to its type.
    Handles cache invalidation and legend updates where required.
    """
    # Invalidate cache when the method exists
    if hasattr(item, "invalidateCache"):
        with suppress(Exception):
            item.invalidateCache()

    # Specific handling for legend items
    if isinstance(item, QgsLayoutItemLegend):
        with suppress(Exception):
            item.updateLegend()

    # General refresh/update sequence
    with suppress(Exception):
        item.refresh()
    with suppress(Exception):
        item.update()


def stabilize_layout(layout: QgsLayout) -> None:
    """Stabilize a layout before export.

    - Refreshes all items safely.
    - Refreshes the layout itself.
    - Processes pending Qt events.
    """
    for item in layout.items():
        # Defensive: continue even if an item misbehaves
        with suppress(Exception):
            _refresh_item(item)

    with suppress(Exception):
        layout.refresh()

    # Process Qt events to ensure the UI thread catches up
    QApplication.processEvents()

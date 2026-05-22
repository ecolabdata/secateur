"""
Common QGIS utilities for PDF export.
"""

from qgis.core import QgsLayout
from qgis.PyQt.QtWidgets import QApplication


def process_qt_events() -> None:
    """Process Qt events to maintain UI responsiveness."""
    QApplication.processEvents()


def safe_refresh_layout(layout: QgsLayout) -> None:
    """Safely refresh a layout."""
    layout.refresh()
    layout.invalidateCache()


def force_qgis_gc() -> None:
    """Force garbage collection for QGIS stability."""
    import gc

    gc.collect()

"""
Common QGIS utilities for PDF export.
"""

from qgis.PyQt.QtWidgets import QApplication


def process_qt_events() -> None:
    """Process Qt events to maintain UI responsiveness."""
    QApplication.processEvents()


def force_qgis_gc() -> None:
    """Force garbage collection for QGIS stability."""
    import gc

    gc.collect()

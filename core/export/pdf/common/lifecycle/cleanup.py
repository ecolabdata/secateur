"""
Deterministic cleanup utilities for PDF export lifecycle.
Ensures Qt events are processed and Python's GC runs to avoid
dangling SIP wrappers after exporting a layout.
"""

import gc

from qgis.PyQt.QtWidgets import QApplication


def finalize_export_cycle() -> None:
    """Force deterministic cleanup after a PDF export.

    - Processes pending Qt events.
    - Runs Python's garbage collector.
    - Processes Qt events again to ensure wrappers are released.
    """
    QApplication.processEvents()
    gc.collect()
    QApplication.processEvents()

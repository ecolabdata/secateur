"""
GeoPDF Export module for Secateur plugin.

This module provides a structured approach to exporting results as GeoPDFs,
with clear separation of concerns and improved maintainability.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from qgis.core import QgsMapLayer, QgsProject


@dataclass(slots=True)
class GeoPdfExportConfig:
    """Configuration for GeoPDF export."""

    output_path: Path
    template_path: Path
    legend_template_path: Path

    title: str
    author: str

    logo_path: Optional[Path] = None

    dpi: int = 300

    export_legend: bool = True
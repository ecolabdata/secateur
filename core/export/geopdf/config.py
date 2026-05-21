"""
GeoPDF Export module for Secateur plugin.

This module provides a structured approach to exporting results as GeoPDFs,
with clear separation of concerns and improved maintainability.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GeoPdfExportConfig:
    """Configuration for GeoPDF export."""

    output_path: Path
    template_path: Path
    legend_template_path: Path

    title: str
    author: str

    logo_path: Path | None = None

    dpi: int = 300

    export_legend: bool = True

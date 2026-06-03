"""
GeoPDF Export module for Secateur plugin.

This module provides a structured approach to exporting results as GeoPDFs,
with clear separation of concerns and improved maintainability.
"""

from dataclasses import dataclass
from pathlib import Path

from ..common.path_resolver import resolve_output_path, resolve_resource_base_path


@dataclass(slots=True)
class GeoPdfExportConfig:
    """Configuration for GeoPDF export."""

    output_path: Path
    template_path: Path

    title: str
    author: str

    logo_path: Path | None = None

    dpi: int = 300

    export_legend: bool = True

    @classmethod
    def default(
        cls,
        output_path: str | Path,
        title: str,
        author: str = "DDT",
        logo_path: str | Path | None = None,
        export_legend: bool = True,
    ) -> "GeoPdfExportConfig":
        """Create a default configuration.

        Handles output path resolution (including directory handling with timestamp),
        sets template paths relative to the project resources directory, and normalises
        optional logo path.
        """
        resource_base = resolve_resource_base_path(__file__)
        output_path_obj, template_path = resolve_output_path(
            output_path, "Rapport_cartographique_GeoPDF_{timestamp}.pdf", resource_base
        )

        return cls(
            output_path=output_path_obj,
            template_path=template_path,
            title=title,
            author=author,
            logo_path=Path(logo_path) if logo_path else None,
            export_legend=export_legend,
        )

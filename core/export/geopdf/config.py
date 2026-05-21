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
        from pathlib import Path

        from ...utils.formatting import timestamp_str

        # Resolve output path; if a directory is provided, create a timestamped filename
        output_path_obj = Path(output_path).expanduser()
        if output_path_obj.is_dir():
            timestamp = timestamp_str()
            output_path_obj = output_path_obj / f"Rapport_cartographique_{timestamp}.pdf"
        else:
            # Ensure parent directories exist
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Determine resource base path (three levels up from this file)
        resource_base = Path(__file__).resolve().parents[3] / "resources"
        template_path = resource_base / "report_page.qpt"
        legend_template_path = resource_base / "legend_layout.qpt"

        return cls(
            output_path=output_path_obj,
            template_path=template_path,
            legend_template_path=legend_template_path,
            title=title,
            author=author,
            logo_path=Path(logo_path) if logo_path else None,
            export_legend=export_legend,
        )

    """Configuration for GeoPDF export."""

    output_path: Path
    template_path: Path
    legend_template_path: Path

    title: str
    author: str

    logo_path: Path | None = None

    dpi: int = 300

    export_legend: bool = True

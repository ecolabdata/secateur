from dataclasses import dataclass
from pathlib import Path

from ..common.export.base_export_config_factory import ExportConfigFactory
from ..common.models.pdf_export_options import PdfExportOptions


@dataclass(slots=True)
class LegendExportConfig(ExportConfigFactory):
    """Configuration for legend export."""

    options: PdfExportOptions
    layer_names: list[str]
    title: str
    author: str
    logo_path: Path | None = None
    max_legend_items_per_page: int = 20

    @classmethod
    def _get_template_filename(cls) -> str:
        """Get the template filename for this configuration type."""
        return "legend_layout.qpt"

    @classmethod
    def _get_default_output_filename(cls, timestamp: str) -> str:
        """Get the default output filename for this configuration type."""
        return f"Legende_{timestamp}.pdf"

    @classmethod
    def default(
        cls,
        *,
        output_path: str | Path,
        layer_names: list[str],
        title: str = "Légende",
        author: str = "QGIS User",
        logo_path: str | Path | None = None,
        max_legend_items_per_page: int = 20,
    ) -> "LegendExportConfig":
        """Create a default configuration.

        Resolves the output path (adds timestamped filename if a directory is given),
        sets the template path to the bundled legend layout, and normalises the logo path.
        """
        # Create base config using parent factory
        base_config = super(LegendExportConfig, cls).default(
            output_path=output_path,
            title=title,
            author=author,
            logo_path=logo_path,
        )

        # Create instance with additional legend-specific parameters
        return cls(
            options=PdfExportOptions(
                output_path=base_config.output_path,
                template_path=base_config.template_path,
                dpi=300,  # Default DPI for legend exports
            ),
            layer_names=layer_names,
            title=base_config.title,
            author=base_config.author,
            logo_path=base_config.logo_path,
            max_legend_items_per_page=max_legend_items_per_page,
        )

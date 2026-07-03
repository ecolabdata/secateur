"""
Configuration objects for Multi-Page PDF export.
"""

from dataclasses import dataclass
from pathlib import Path

from qgis.core import QgsMapLayer, QgsProcessingFeedback

from ..common.export.base_export_config_factory import ExportConfigFactory
from ..common.models.pdf_export_options import PdfExportOptions


@dataclass(slots=True)
class MultiPagePdfExportConfig(ExportConfigFactory):
    """Configuration object for multi-page PDF export settings.

    Stores all parameters needed for generating multi-page PDF reports including
    export options, metadata, and layer information.

    Attributes:
        options: PDF export options including output path and template path
        title: Document title for the PDF
        author: Author metadata for the PDF
        logo_path: Optional path to logo image file
        result_layers: List of result layers to include in the report
        basemap_layer: Optional basemap layer to display with result layers
        feedback: Optional QGIS processing feedback object for progress updates
    """

    options: PdfExportOptions

    title: str
    author: str

    logo_path: Path | None = None
    # high dpi cause large export
    # dpi is now part of PdfExportOptions

    # These fields are needed for the export process
    result_layers: list[QgsMapLayer] | None = None
    basemap_layer: QgsMapLayer | None = None
    feedback: QgsProcessingFeedback | None = None

    @classmethod
    def _get_template_filename(cls) -> str:
        """Get the template filename for this configuration type."""
        return "report_page.qpt"

    @classmethod
    def _get_default_output_filename(cls, timestamp: str) -> str:
        """Get the default output filename for this configuration type."""
        return f"Rapport_cartographique_multipage_{timestamp}.pdf"

    @classmethod
    def default(
        cls,
        output_path: str | Path,
        title: str,
        author: str,
        logo_path: str | Path | None,
    ) -> "MultiPagePdfExportConfig":
        """Create a default configuration with common setup.

        Resolves the output path (adds timestamped filename if a directory is given),
        sets the template path to the bundled layout, and normalises the logo path.
        """
        # Create base config using parent factory
        base_config = super(MultiPagePdfExportConfig, cls).default(
            output_path=output_path,
            title=title,
            author=author,
            logo_path=logo_path,
        )

        # Create instance with additional multipage-specific parameters
        return cls(
            options=PdfExportOptions(
                output_path=base_config.output_path,
                template_path=base_config.template_path,
                dpi=150,  # Default DPI for multipage exports
            ),
            title=base_config.title,
            author=base_config.author,
            logo_path=base_config.logo_path,
        )

    def with_export_params(
        self,
        result_layers: list[QgsMapLayer] | None = None,
        basemap_layer: QgsMapLayer | None = None,
        feedback: QgsProcessingFeedback | None = None,
    ) -> "MultiPagePdfExportConfig":
        """Create a new config with export-specific parameters."""
        return MultiPagePdfExportConfig(
            options=PdfExportOptions(
                output_path=self.options.output_path,
                template_path=self.options.template_path,
                dpi=self.options.dpi,
            ),
            title=self.title,
            author=self.author,
            logo_path=self.logo_path,
            result_layers=result_layers,
            basemap_layer=basemap_layer,
            feedback=feedback,
        )

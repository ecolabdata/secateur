"""
GeoPDF Export Service module.

This module provides the main service for orchestrating GeoPDF exports,
handling the coordination between various components while keeping
the logic centralized and clean.
"""

from pathlib import Path

from qgis.core import (
    QgsLayout,
    QgsMapLayer,
    QgsProcessingFeedback,
    QgsProject,
    QgsRectangle,
)

from ...logger import logger
from ...utils.feedback import update_feedback
from ...utils.formatting import display_date_str
from ..pdf.common.models import PdfExportOptions
from ..pdf.common.pdf_export import export_layout_to_pdf
from .config import GeoPdfExportConfig
from .extent import compute_export_extent, get_source_vector_layer
from .layout import build_report_layout
from .visibility import temporary_visible_layers


class GeoPdfExportService:
    """Service for orchestrating GeoPDF exports."""

    def __init__(self, project: QgsProject, config: GeoPdfExportConfig):
        """Initialize the export service with project and configuration."""
        self.project = project
        self.config = config

    def export(
        self,
        result_layers: list[QgsMapLayer],
        basemap_layer: QgsMapLayer | None = None,
        feedback: QgsProcessingFeedback | None = None,
    ) -> str:
        """Export results to GeoPDF using the configured settings."""
        # Compute extent
        extent_rect = self._prepare_extent(result_layers)
        # Build layout with proper visibility handling
        layout = self._build_layout(result_layers, extent_rect, basemap_layer, feedback)
        # Export legend if needed (requires layer names)
        self._export_legend_if_needed(layout, result_layers, feedback)
        # Export the GeoPDF file
        output_path = self._export_geopdf(layout, feedback)
        return str(output_path)

    # --- Private helper methods ---
    def _prepare_extent(self, result_layers: list[QgsMapLayer]) -> "QgsRectangle":
        """Validate inputs, compute source layer and extent rectangle."""
        src_layer = get_source_vector_layer(result_layers)
        return compute_export_extent(src_layer)

    def _build_layout(
        self,
        result_layers: list[QgsMapLayer],
        extent_rect: "QgsRectangle",
        basemap_layer: QgsMapLayer | None,
        feedback: QgsProcessingFeedback | None,
    ) -> "QgsLayout":
        """Create and configure the QGIS layout for the export, handling visibility of result layers."""
        update_feedback(feedback, 0, "Préparation de l'export PDF…")
        root = self.project.layerTreeRoot()
        # Use temporary visibility for result layers and basemap during layout building
        with temporary_visible_layers(root, result_layers, basemap_layer, feedback) as _:
            template_path_obj = Path(self.config.template_path)
            if not template_path_obj.is_file():
                logger.error(f"Layout template not found: {template_path_obj}")
                raise RuntimeError(f"Layout template not found: {template_path_obj}")

            layout = build_report_layout(
                project=self.project,
                template_path=str(self.config.template_path),
                date_hm=display_date_str(),
                extent_rect=extent_rect,
                logo_path=str(self.config.logo_path) if self.config.logo_path else None,
                title=self.config.title,
                author=self.config.author,
            )
            update_feedback(feedback, 40, "Template QPT chargé")
            update_feedback(feedback, 50, "Carte configurée")
            update_feedback(feedback, 60, "Textes injectés")
            update_feedback(feedback, 70, "Logo injecté")
            return layout

    def _export_legend_if_needed(
        self, layout: "QgsLayout", result_layers: list[QgsMapLayer], feedback: QgsProcessingFeedback | None
    ) -> None:
        """Export a legend PDF when the configuration requests it,
        using the given result layers for layer name collection."""
        if not self.config.export_legend:
            return
        try:
            from ...legend_exporter import export_legend

            legend_output_path = (
                self.config.output_path.parent
                / f"Legende_GeoPDF_{self.config.output_path.name.replace('.pdf', '')}.pdf"
            )
            # Use temporary visibility to collect layer names for the legend
            root = self.project.layerTreeRoot()
            with temporary_visible_layers(root, result_layers, None, feedback) as layer_names:
                export_legend(
                    template_path=str(self.config.legend_template_path),
                    output_path=str(legend_output_path),
                    layer_names=layer_names,
                    logo_path=str(self.config.logo_path) if self.config.logo_path else None,
                    title=self.config.title,
                    author=self.config.author,
                )
        except Exception as e:
            logger.warning(f"External legend export failed: {e}")

    def _export_geopdf(self, layout: "QgsLayout", feedback: QgsProcessingFeedback | None) -> Path:
        """Delegate heavy export logic to GeoPdfExporter infrastructure class."""
        # Prepare settings
        update_feedback(feedback, 80, "Export du GeoPDF en cours")

        # Create options for PDF export
        options = PdfExportOptions(
            dpi=self.config.dpi,
            write_geopdf=True,
            force_vector_output=True,
            export_layers_as_vectors=True,
            export_metadata=True,
        )

        output_path = Path(self.config.output_path)
        # Use common export function
        result_path = export_layout_to_pdf(layout=layout, output_path=output_path, options=options)
        update_feedback(feedback, 100, "Export terminé")
        return result_path

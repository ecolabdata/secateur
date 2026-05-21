"""
GeoPDF Export Service module.

This module provides the main service for orchestrating GeoPDF exports,
handling the coordination between various components while keeping
the logic centralized and clean.
"""

from pathlib import Path
import os
from typing import List, Optional

from qgis.core import QgsLayoutExporter, QgsMapLayer, QgsProject, QgsProcessingFeedback

from...logger import logger
from...utils.feedback import update_feedback
from...utils.layouts import clean_layouts
from...utils.rendering import is_simple_fill, set_layer_opacity
from...utils.visibility import clear_all_visibility, set_layer_and_parents_visible
from .config import GeoPdfExportConfig
from .extent import compute_export_extent, get_source_vector_layer
from .layout_builder import build_report_layout
from .visibility import temporary_visible_layers


class GeoPdfExportService:
    """Service for orchestrating GeoPDF exports."""

    def __init__(self, project: QgsProject, config: GeoPdfExportConfig):
        """Initialize the export service with project and configuration."""
        self.project = project
        self.config = config

    def export(self, result_layers: List[QgsMapLayer], basemap_layer: Optional[QgsMapLayer] = None, feedback: QgsProcessingFeedback | None = None) -> str:
        """
        Export results to GeoPDF using the configured settings.

        Args:
            result_layers: List of layers to include in the export
            basemap_layer: Optional basemap layer to include

        Returns:
            The path to the exported PDF file
        """
        # 1. Validate inputs
        src_layer = get_source_vector_layer(result_layers)
        
        # 2. Compute extent from first result layer
        extent_rect = compute_export_extent(src_layer)
        
        # 3. Manage layer visibility and obtain legend names
        update_feedback(feedback, 0, "Préparation de l'export PDF…")
        root = self.project.layerTreeRoot()
        with temporary_visible_layers(root, result_layers, basemap_layer, feedback) as layer_names:
            # 4. Build layout
            # Verify template path exists
            template_path_obj = Path(self.config.template_path)
            if not template_path_obj.is_file():
                logger.error(f"Layout template not found: {template_path_obj}")
                raise RuntimeError(f"Layout template not found: {template_path_obj}")

            layout = build_report_layout(
                project=self.project,
                template_path=str(self.config.template_path),
                date_hm=None,  # This will be handled internally
                extent_rect=extent_rect,
                logo_path=str(self.config.logo_path) if self.config.logo_path else None,
                title=self.config.title,
                author=self.config.author,
                basemap_layer=basemap_layer,
            )
            # Update feedback after layout creation steps
            update_feedback(feedback, 40, "Template QPT chargé")
            update_feedback(feedback, 50, "Carte configurée")
            update_feedback(feedback, 60, "Textes injectés")
            update_feedback(feedback, 70, "Logo injecté")
            
            # 5. Export legend if requested
            if self.config.export_legend:
                try:
                    # Import here to avoid circular imports
                    from ...legend_exporter import export_legend
                    legend_output_path = self.config.output_path.parent / f"Legende_GeoPDF_{self.config.output_path.name.replace('.pdf', '')}.pdf"
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

            # 6. Export GeoPDF
            update_feedback(feedback, 80, "Export du GeoPDF en cours")
            exporter = QgsLayoutExporter(layout)
            settings = QgsLayoutExporter.PdfExportSettings()
            settings.dpi = self.config.dpi
            settings.writeGeoPdf = True
            settings.forceVectorOutput = True
            settings.exportLayersAsVectors = True
            settings.exportMetadata = True

            # Ensure output directory exists
            output_path = Path(self.config.output_path)
            # Remove existing file if it exists to avoid lock issues
            if output_path.is_file():
                try:
                    output_path.unlink()
                    logger.debug(f"Removed existing PDF file: {output_path}")
                except Exception as rm_err:
                    logger.warning(f"Could not remove existing PDF file {output_path}: {rm_err}")
            # Validate output path
            if output_path.suffix.lower() != '.pdf':
                logger.error(f"Invalid output file extension: {output_path.suffix}")
                raise RuntimeError(f"Output file must have .pdf extension, got {output_path.suffix}")

            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured output directory exists: {output_path.parent}")
            except Exception as dir_err:
                logger.error(f"Failed to create output directory {output_path.parent}: {dir_err}")
                raise RuntimeError(f"Cannot create output directory: {dir_err}")

            # Diagnostic logging
            logger.debug(f"PDF export absolute path: {output_path.resolve()}")
            logger.debug(f"Path exists: {output_path.exists()}")
            logger.debug(f"Writable directory: {os.access(output_path.parent, os.W_OK)}")
            # Test write permission by creating a temporary file
            test_file = output_path.parent / ".__kilo_write_test"
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                test_file.unlink()
                logger.debug("Write permission test succeeded.")
            except Exception as wf_err:
                logger.error(f"Write permission test failed: {wf_err}")
                raise RuntimeError(f"Cannot write to output directory: {wf_err}")

            try:
                # Ensure layout is fully refreshed before export
                layout.refresh()
                exporter.layout().refresh()

                from qgis.PyQt.QtWidgets import QApplication
                QApplication.processEvents()

                logger.debug(f"Layout items count: {len(layout.items())}")
                if len(layout.items()) == 0:
                    raise RuntimeError("Layout contains no items; template may have failed to load.")
                result = exporter.exportToPdf(str(output_path), settings)
                # If GeoPDF export fails with code 4, retry without GeoPDF flag for debugging
                if result != QgsLayoutExporter.Success and result == 4:
                    logger.debug("Initial GeoPDF export failed with code 4; retrying without GeoPDF flag.")
                    settings.writeGeoPdf = False
                    result = exporter.exportToPdf(str(output_path), settings)

                QApplication.processEvents()

                if result != QgsLayoutExporter.Success:
                    # Attempt to get detailed error info if available
                    error_msg = exporter.errorMessage() if hasattr(exporter, "errorMessage") else ""
                    error_file = exporter.errorFile() if hasattr(exporter, "errorFile") else ""
                    raise RuntimeError(
                        f"PDF export failed with code: {result}. Details: {error_msg} File: {error_file}"
                    )

                logger.info(f"GeoPDF exported to: {output_path}")
                update_feedback(feedback, 100, "Export terminé")

            except Exception as e:
                logger.error(f"GeoPDF export failed: {e}")
                raise RuntimeError(f"GeoPDF export failed: {e}") from e
            finally:
                # Clean up any temporary layouts created during the context
                manager = self.project.layoutManager()
                clean_layouts(manager)

        return str(self.config.output_path)
"""
Multi-Page PDF Export Service module.

This module provides the main service for orchestrating multi-page PDF exports,
handling the coordination between various components while keeping
the logic centralized and clean.
"""

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from qgis.core import QgsLayout, QgsMapLayer, QgsProcessingFeedback, QgsProject, QgsRectangle

from ....utils.feedback import update_feedback
from ..common.layout.extent import (
    compute_export_extent,
    get_source_vector_layer,
)
from ..common.models import PdfExportOptions
from ..common.pdf_export import export_layout_to_pdf
from ..legend.service import merge_pdfs
from .config import MultiPagePdfExportConfig
from .layout import build_pdf_page_layout


class MultiPagePdfExportService:
    def __init__(
        self,
        project: QgsProject,
        config: MultiPagePdfExportConfig,
    ) -> None:
        self.project = project
        self.config = config

    def export(
        self,
        result_layers: list[QgsMapLayer],
        basemap_layer: QgsMapLayer | None = None,
        feedback: QgsProcessingFeedback | None = None,
    ) -> str:
        src_layer = get_source_vector_layer(result_layers)

        extent_rect = compute_export_extent(src_layer)

        total_pages = 1 + max(0, len(result_layers) - 1)

        # Create PDF export options
        options = PdfExportOptions(
            dpi=self.config.dpi,
            write_geopdf=False,
            force_vector_output=False,
            export_layers_as_vectors=False,
            export_metadata=True,
            rasterize_whole_image=True,
        )

        # Create temporary directory for per-page PDFs
        with TemporaryDirectory() as tmp_dir:
            temp_dir = Path(tmp_dir)
            tmp_files: list[Path] = []

            # -----------------------------------------------------------------
            # Overview page
            # -----------------------------------------------------------------
            update_feedback(feedback, 0, "Création de la page d'ensemble")
            overview_layers: list[QgsMapLayer] = [src_layer]
            if basemap_layer:
                overview_layers.append(basemap_layer)
            overview_layout = self._create_page_layout(
                title=self.config.title,
                layers=overview_layers,
                extent_rect=extent_rect,
            )
            overview_path = temp_dir / "overview.pdf"
            export_layout_to_pdf(layout=overview_layout, output_path=overview_path, options=options)
            tmp_files.append(overview_path)

            # -----------------------------------------------------------------
            # Detail pages
            # -----------------------------------------------------------------
            if len(result_layers) >= 2:
                intersection_layer = result_layers[0]
                for idx, layer in enumerate(result_layers[1:], start=1):
                    progress = int(idx * 90 / total_pages)
                    update_feedback(feedback, progress, f"Création page {layer.name()}")
                    page_layers = [intersection_layer, layer]
                    if basemap_layer:
                        page_layers.append(basemap_layer)
                    layout = self._create_page_layout(
                        title=layer.name().removesuffix(" — résultat"),
                        layers=page_layers,
                        extent_rect=extent_rect,
                    )
                    page_path = temp_dir / f"page_{idx}.pdf"
                    export_layout_to_pdf(layout=layout, output_path=page_path, options=options)
                    tmp_files.append(page_path)

            # -----------------------------------------------------------------
            # Merge PDFs if more than one page
            # -----------------------------------------------------------------
            # Determine final output file path; if a directory is provided or
            # the path lacks a .pdf suffix, create a default PDF filename inside it
            final_path = Path(self.config.output_path)
            if len(tmp_files) == 1:
                shutil.move(str(tmp_files[0]), str(final_path))
            else:
                merge_pdfs(tmp_files, final_path)

        update_feedback(feedback, 100, "Export PDF terminé")
        return str(final_path)

    def _create_page_layout(self, title: str, layers: list[QgsMapLayer], extent_rect: QgsRectangle) -> QgsLayout:
        """Helper to create a PDF page layout with consistent parameters."""
        return build_pdf_page_layout(
            project=self.project,
            template_path=self.config.template_path,
            extent_rect=extent_rect,
            visible_layers=layers,
            title=title,
            author=self.config.author,
            logo_path=self.config.logo_path,
        )

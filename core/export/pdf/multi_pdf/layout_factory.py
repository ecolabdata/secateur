"""
Multi-Page PDF Layout Factory module.

This module provides a factory for creating individual page layouts
for multi-page PDF exports, separating the page creation logic from
the service coordinator.
"""

from typing import TYPE_CHECKING

from qgis.core import QgsMapLayer, QgsPrintLayout, QgsProject

from ....utils.feedback import update_feedback
from ..common.layout.extent import (
    compute_export_extent,
    get_source_vector_layer,
)
from .page_builder import MultiPagePageBuilder

if TYPE_CHECKING:
    from .config import MultiPagePdfExportConfig


from ..common.export.collaborators import LayoutFactory


class MultiPageLayoutFactory(LayoutFactory):
    """Factory for creating individual page layouts for multi-page PDF exports.

    Creates a series of QgsPrintLayout objects representing pages in a multi-page
    PDF report. Generates both overview and detail pages based on the provided
    result layers and configuration.

    The factory produces:
    - One overview page showing all result layers
    - Additional detail pages for each result layer beyond the first

    Attributes:
        project: QGIS project instance
        config: Multi-page PDF export configuration
        page_builder: Helper for creating individual page layouts
    """

    def __init__(
        self,
        project: QgsProject,
        config: "MultiPagePdfExportConfig",
    ) -> None:
        self.project = project
        self.config = config
        self.page_builder = MultiPagePageBuilder(project, config)

    def create_layouts(self) -> list[QgsPrintLayout]:
        """Create layouts for export as required by LayoutFactory interface."""
        # Reuse existing page building logic
        return self.build_pages()

    def build_pages(self) -> list[QgsPrintLayout]:
        """Build all pages for the multi-page PDF export."""
        result_layers = self.config.result_layers
        basemap_layer = self.config.basemap_layer
        feedback = self.config.feedback

        if not result_layers:
            raise ValueError("result_layers must be provided for MultiPagePdfExportService")

        src_layer = get_source_vector_layer(result_layers)
        extent_rect = compute_export_extent(src_layer)
        total_pages = 1 + max(0, len(result_layers) - 1)

        layouts = []

        # -----------------------------------------------------------------
        # Overview page
        # -----------------------------------------------------------------
        update_feedback(feedback, 0, "Création de la page d'ensemble")
        overview_layers: list[QgsMapLayer] = [src_layer]
        if basemap_layer:
            overview_layers.append(basemap_layer)
        overview_layout = self.page_builder.create_overview_page(
            title=self.config.title,
            layers=overview_layers,
            extent_rect=extent_rect,
        )
        layouts.append(overview_layout)

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
                layout = self.page_builder.create_detail_page(
                    title=layer.name().removesuffix(" — résultat"),
                    layers=page_layers,
                    extent_rect=extent_rect,
                )
                layouts.append(layout)

        return layouts

"""
Multi-Page PDF Page Builder module.

This module provides a factory for creating individual page layouts
for multi-page PDF exports, separating page creation logic from
service coordination.
"""

from typing import TYPE_CHECKING

from qgis.core import QgsMapLayer, QgsPrintLayout, QgsProject, QgsRectangle

from .layout import MultiPdfLayout

if TYPE_CHECKING:
    from .config import MultiPagePdfExportConfig


class MultiPagePageBuilder:
    """Builder for creating individual page layouts for multi-page PDF exports.

    Responsible for constructing individual page layouts with appropriate
    layers, extent, and metadata for inclusion in multi-page PDF reports.

    Provides methods for creating both overview pages (showing all layers)
    and detail pages (showing specific layer combinations).

    Attributes:
        project: QGIS project instance
        config: Multi-page PDF export configuration
    """

    def __init__(
        self,
        project: QgsProject,
        config: "MultiPagePdfExportConfig",
    ) -> None:
        self.project = project
        self.config = config

    def create_overview_page(
        self,
        title: str,
        layers: list[QgsMapLayer],
        extent_rect: QgsRectangle,
    ) -> QgsPrintLayout:
        """Create an overview page layout showing all layers."""
        layout_builder = MultiPdfLayout.build(
            project=self.project,
            template_path=self.config.options.template_path,
            extent_rect=extent_rect,
            visible_layers=layers,
            title=title,
            author=self.config.author,
            logo_path=self.config.logo_path,
        )

        return layout_builder.layout

    def create_detail_page(
        self,
        title: str,
        layers: list[QgsMapLayer],
        extent_rect: QgsRectangle,
    ) -> QgsPrintLayout:
        """Create a detail page layout for a specific layer combination."""
        layout_builder = MultiPdfLayout.build(
            project=self.project,
            template_path=self.config.options.template_path,
            extent_rect=extent_rect,
            visible_layers=layers,
            title=title,
            author=self.config.author,
            logo_path=self.config.logo_path,
        )

        return layout_builder.layout

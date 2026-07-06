"""
Multi-Page PDF Export Service module.

This module provides the main service for orchestrating multi-page PDF exports,
handling the coordination between various components while keeping
the logic centralized and clean.
"""

from pathlib import Path

from qgis.core import QgsProject

from ..common.export.base_export_service import BasePdfExportService
from ..common.export.collaborators import (
    DefaultExportLifecycle,
    DefaultLayoutStabilizer,
    DefaultPdfExporter,
    DefaultPdfMerger,
)
from ..common.models import PdfExportOptions
from .config import MultiPagePdfExportConfig
from .layout_factory import MultiPageLayoutFactory


class MultiPagePdfExportService(BasePdfExportService):
    """Service for orchestrating multi-page PDF exports.

    This service coordinates the creation of multi-page PDF reports from QGIS map layers,
    handling layout generation, PDF export, and final merging of pages.

    The service implements the collaborator pattern, delegating specific tasks to:
    - MultiPageLayoutFactory: Creates individual page layouts
    - DefaultPdfExporter: Handles PDF generation per page
    - DefaultPdfMerger: Merges multiple pages into a single PDF
    - DefaultExportLifecycle: Manages cleanup operations
    - DefaultLayoutStabilizer: Ensures consistent layout rendering
    """

    def __init__(
        self,
        project: QgsProject,
        config: MultiPagePdfExportConfig,
    ) -> None:
        self.project = project
        self.config = config

        # Create collaborators
        layout_factory = MultiPageLayoutFactory(
            project=self.project,
            config=self.config,
        )
        exporter = DefaultPdfExporter()
        pdf_merger = DefaultPdfMerger()
        lifecycle = DefaultExportLifecycle()
        stabilizer = DefaultLayoutStabilizer()

        # Initialize base service with collaborators
        super().__init__(
            layout_factory=layout_factory,
            exporter=exporter,
            pdf_merger=pdf_merger,
            lifecycle=lifecycle,
            stabilizer=stabilizer,
        )

    @property
    def output_path(self) -> Path:
        return self.config.options.output_path

    @property
    def export_options(self) -> PdfExportOptions:
        return self.config.options

from pathlib import Path

from qgis.core import QgsPrintLayout, QgsProject, QgsVectorLayer

from ..common.export.base_export_service import BasePdfExportService
from ..common.export.collaborators import (
    DefaultExportLifecycle,
    DefaultLayoutFactory,
    DefaultLayoutStabilizer,
    DefaultPdfExporter,
    DefaultPdfMerger,
)
from ..common.models.metadata import LayoutMetadataFactory
from .config import LegendExportConfig
from .layout import LegendLayout
from .pagination import LegendCostCalculator, LegendPaginator


class LegendExportService(BasePdfExportService):
    """Export legend PDF using the new architecture."""

    def __init__(self, project: QgsProject, config: LegendExportConfig) -> None:
        self.project = project
        self.config = config
        self.calculator = LegendCostCalculator()
        self.paginator = LegendPaginator(
            project=project,
            max_items_per_page=config.max_legend_items_per_page,
        )

        # Create layouts for the factory
        layouts = self._create_layouts()

        # Create collaborators
        layout_factory = DefaultLayoutFactory(layouts)
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

    def _create_layouts(self) -> list[QgsPrintLayout]:
        """Create layouts for legend export."""
        layouts: list[QgsPrintLayout] = []

        # Calculate costs for all layers first
        layer_costs = []
        layers_by_name = {layer.name(): layer for layer in self.project.mapLayers().values()}
        for layer_name in self.config.layer_names:
            layer = layers_by_name.get(layer_name)

            if not layer:
                # Fallback cost for missing layers
                layer_costs.append(5)
                continue

            # Fallback cost for non-vector layers
            if not isinstance(layer, QgsVectorLayer):
                layer_costs.append(5)
            else:
                layer_costs.append(self.calculator.calculate(layer))

        pages = self.paginator.paginate(self.config.layer_names, layer_costs)
        for page_number, page in enumerate(pages, start=1):
            metadata = LayoutMetadataFactory.create(
                title=self.config.title,
                author=self.config.author,
                logo_path=self.config.logo_path,
            )
            layout = LegendLayout.build(
                project=self.project,
                template_path=self.config.options.template_path,
                metadata=metadata,
                layer_names=page.layer_names,
                page_number=page_number,
                total_pages=len(pages),
            )
            layouts.append(layout.layout)
        return layouts

    @property
    def output_path(self) -> Path:
        return self.config.options.output_path

    @property
    def export_options(self):
        return self.config.options

import gc
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from pypdf import PdfWriter
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsGraduatedSymbolRenderer,
    QgsLayerTree,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsRuleBasedRenderer,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument

from .logger import logger


@dataclass(slots=True)
class LegendExportConfig:
    """Configuration for legend export."""

    template_path: Path
    output_path: Path
    layer_names: list[str]
    logo_path: Path | None = None
    per_page: int = 10
    max_legend_items_per_page: int = 20
    dpi: int = 300
    title: str = "Légende"
    author: str = "QGIS User"


class LegendItemCounter:
    """Calculate the logical cost of a layer for legend pagination."""

    def count(self, layer: QgsVectorLayer) -> int:
        """
        Calculate the cost of a layer in terms of legend items.

        Cost is calculated based on:
        - Title (always 1)
        - Symbols (1 each)
        - Categories (1 each)
        - Ranges (1 each)
        - Rules (1 each)
        """
        renderer = layer.renderer()
        if renderer is None:
            logger.warning(f"Layer '{layer.name()}' has no renderer, using fallback cost of 5")
            return 5

        # Determine renderer type and calculate cost
        if isinstance(renderer, QgsSingleSymbolRenderer):
            # 1 title + 1 symbol = 2
            return 2

        elif isinstance(renderer, QgsCategorizedSymbolRenderer):
            # 1 title + number of categories
            categories = renderer.categories()
            return 1 + len(categories)

        elif isinstance(renderer, QgsGraduatedSymbolRenderer):
            # 1 title + number of ranges
            ranges = renderer.ranges()
            return 1 + len(ranges)

        elif isinstance(renderer, QgsRuleBasedRenderer):
            # 1 title + number of visible rules (recursive)
            return 1 + self._count_rules(renderer.rootRule())

        else:
            # Fallback for unknown renderers
            logger.warning(
                f"Unknown renderer type for layer '{layer.name()}': {type(renderer).__name__}, using fallback cost of 5"
            )
            return 5

    def _count_rules(self, rule) -> int:
        """
        Recursively count active legend rules.

        Only counts rules that are active and have symbols.
        """
        if not rule:
            return 0

        count = 0

        # Count only active rules with symbols
        if rule.isActive() and rule.symbol() is not None:
            count += 1

        # Recursively count child rules
        for child_rule in rule.children():
            count += self._count_rules(child_rule)

        return count


class LegendPaginationService:
    """
    Paginate layers based on their estimated legend item cost.
    """

    def __init__(
        self,
        project: QgsProject,
        counter: LegendItemCounter,
        max_items_per_page: int,
    ):
        self.project = project
        self.counter = counter
        self.max_items_per_page = max_items_per_page

    def paginate(self, layer_names: list[str]) -> list[list[str]]:
        """
        Paginate layers according to their legend complexity.

        Strategy:
        - accumulate layers until max_items_per_page is reached
        - if a single layer exceeds the limit, place it alone
        """
        if not layer_names:
            raise ValueError("No layers provided for export")

        pages: list[list[str]] = []

        current_page: list[str] = []
        current_cost = 0

        for layer_name in layer_names:
            layers = self.project.mapLayersByName(layer_name)

            if not layers:
                logger.warning(f"Layer '{layer_name}' not found in project")
                continue

            layer = layers[0]

            # Fallback cost for non-vector layers
            if not isinstance(layer, QgsVectorLayer):
                logger.warning(f"Layer '{layer_name}' is not a vector layer, using fallback cost of 5")
                layer_cost = 5
            else:
                layer_cost = self.counter.count(layer)

            logger.debug(f"Layer '{layer_name}' legend cost = {layer_cost}")

            # If adding this layer exceeds page budget,
            # flush current page first
            if current_page and (current_cost + layer_cost > self.max_items_per_page):
                pages.append(current_page)

                current_page = []
                current_cost = 0

            current_page.append(layer_name)
            current_cost += layer_cost

        # Final page
        if current_page:
            pages.append(current_page)
            logger.info(f"Created page with cost={current_cost} and {len(current_page)} layers")

        logger.info(f"Pagination complete: {len(pages)} page(s) generated")

        logger.info(f"Pagination complete: {len(pages)} page(s) generated")

        return pages


class LayoutFactory:
    """Factory for creating new layouts from templates."""

    def __init__(self, template_path: Path):
        self.template_path = template_path
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

    def create_layout(self, project: QgsProject) -> QgsPrintLayout:
        """Create a new layout from template."""
        layout = QgsPrintLayout(project)

        doc = QDomDocument()
        with open(self.template_path, encoding="utf-8") as f:
            success = doc.setContent(f.read())

        if not success:
            raise RuntimeError(f"Invalid QPT template: {self.template_path}")

        context = QgsReadWriteContext()
        _, ok = layout.loadFromTemplate(doc, context, clearExisting=True)

        if not ok:
            raise RuntimeError(f"Failed to load template: {self.template_path}")

        return layout


class LegendLayoutBuilder:
    """Builds a single legend page layout."""

    def __init__(
        self,
        project: QgsProject,
        layout: QgsPrintLayout,
        title: str,
        author: str,
        logo_path: Path | None,
    ):
        self.project = project
        self.layout = layout
        self.title = title
        self.author = author
        self.logo_path = logo_path
        # Persistent root for this builder instance
        self.root = QgsLayerTree()
        self.root.setName("LegendRoot")

    def build(self, layer_names: list[str], page_number: int, total_pages: int):
        """Build the layout with given layers and metadata."""
        # Clear the root for this page
        self.root.clear()

        # Retrieve template items
        legend = cast(
            QgsLayoutItemLegend | None,
            self.layout.itemById("legend"),
        )
        title_item = cast(
            QgsLayoutItemLabel | None,
            self.layout.itemById("title"),
        )
        author_item = cast(
            QgsLayoutItemLabel | None,
            self.layout.itemById("author"),
        )
        date_item = cast(
            QgsLayoutItemLabel | None,
            self.layout.itemById("date"),
        )
        logo_item = cast(
            QgsLayoutItemPicture | None,
            self.layout.itemById("logo"),
        )

        # Validate required items
        if legend is None:
            raise ValueError("Required legend item with ID 'legend' not found in template")

        # Disable auto-update model
        legend.setAutoUpdateModel(False)

        # Add layers to tree
        layers_added = 0
        for name in layer_names:
            layers = self.project.mapLayersByName(name)
            if not layers:
                logger.warning(f"Layer '{name}' not found in project")
                continue

            # Take the first layer with matching name and clone it for safety
            self.root.addLayer(layers[0])
            layers_added += 1

        if layers_added == 0:
            raise RuntimeError(f"No valid layers found for page {page_number}")

        # Inject layer tree into legend
        legend.model().setRootGroup(self.root)

        # Refresh legend with proper sequence for QGIS 3.34
        legend.invalidateCache()
        legend.updateLegend()
        legend.refresh()
        legend.adjustBoxSize()

        self.layout.refresh()

        # Setup text items
        self._setup_texts(title_item, author_item, date_item, logo_item, page_number, total_pages)

    def _setup_texts(
        self,
        title_item: QgsLayoutItemLabel | None,
        author_item: QgsLayoutItemLabel | None,
        date_item: QgsLayoutItemLabel | None,
        logo_item: QgsLayoutItemPicture | None,
        page_number: int,
        total_pages: int,
    ):
        """Setup the text items in the layout."""
        # Set up title
        if title_item:
            title_item.setText(f"{self.title} - Page {page_number}/{total_pages}")
            title_item.setVisible(True)

        # Set up author
        if author_item:
            author_item.setText(f"Auteur: {self.author}")
            author_item.setVisible(True)

        # Set up date
        if date_item:
            date_item.setText(datetime.now().strftime("%d/%m/%Y"))
            date_item.setVisible(True)

        # Set up logo
        if logo_item:
            if self.logo_path:
                logo_item.setPicturePath(str(self.logo_path))
                logo_item.refresh()
                logo_item.setVisible(True)
            else:
                logo_item.setVisible(False)


class PdfPageExporter:
    """Exports individual layout pages to PDF."""

    def __init__(self, config: LegendExportConfig):
        self.config = config
        if self.config.logo_path and not self.config.logo_path.exists():
            raise FileNotFoundError(f"Logo file not found: {self.config.logo_path}")

    def export(self, layout: QgsPrintLayout, output_path: Path) -> None:
        """Export layout to PDF."""
        exporter = QgsLayoutExporter(layout)
        settings = QgsLayoutExporter.PdfExportSettings()
        settings.dpi = self.config.dpi

        result = exporter.exportToPdf(str(output_path), settings)

        if result != QgsLayoutExporter.Success:
            raise RuntimeError(f"PDF export failed with code={result}")


class PdfMergerService:
    """Merges individual PDF pages into a single PDF."""

    def __init__(self):
        pass

    def merge(self, pdf_paths: list[Path], output_path: Path) -> None:
        """Merge multiple PDF files into one."""
        writer = PdfWriter()

        for pdf_path in pdf_paths:
            writer.append(str(pdf_path))

        with open(output_path, "wb") as f:
            writer.write(f)
        writer.close()  # Important for Windows/QGIS


class LegendExportService:
    """Main service for exporting legends with new pipeline."""

    def __init__(
        self,
        project: QgsProject,
        config: LegendExportConfig,
    ):
        self.project = project
        self.config = config
        self.counter = LegendItemCounter()
        self.paginator = LegendPaginationService(
            project=project,
            counter=self.counter,
            max_items_per_page=config.max_legend_items_per_page,
        )
        self.layout_factory = LayoutFactory(config.template_path)
        self.page_exporter = PdfPageExporter(config)
        self.merger_service = PdfMergerService()

    def export(self) -> str:
        """Execute the complete export pipeline."""
        # Paginate layers
        chunks = self.paginator.paginate(self.config.layer_names)
        total_pages = len(chunks)

        # Create temporary directory for page PDFs
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            page_paths = []

            # Process each page
            for page_index, layer_chunk in enumerate(chunks, 1):
                logger.info(f"Exporting page {page_index}/{total_pages}")

                # Create new layout for this page
                layout = self.layout_factory.create_layout(self.project)

                # Build the layout
                builder = LegendLayoutBuilder(
                    project=self.project,
                    layout=layout,
                    title=self.config.title,
                    author=self.config.author,
                    logo_path=self.config.logo_path,
                )
                builder.build(layer_chunk, page_index, total_pages)

                # Export page to PDF
                page_path = tmp_path / f"legend_page_{page_index:03d}.pdf"
                self.page_exporter.export(layout, page_path)
                page_paths.append(page_path)

                del builder
                del layout
                gc.collect()

            # Merge all pages
            self.merger_service.merge(page_paths, self.config.output_path)
            logger.info(f"Final PDF exported to: {self.config.output_path}")

            # Force garbage collection for Windows/QGIS stability
            gc.collect()

        return str(self.config.output_path)


def export_legend(
    template_path: str,
    output_path: str,
    layer_names: list[str],
    logo_path: str | None = None,
    max_legend_items_per_page: int = 20,
    dpi: int = 300,
    title: str = "Légende",
    author: str = "QGIS User",
) -> str:
    """
    Export a legend using a new deterministic pipeline.

    This function creates a new legend PDF by:
    1. Paginating layers into pages based on legend item cost
    2. Creating a new layout for each page
    3. Building each page with appropriate layers
    4. Exporting each page to PDF
    5. Merging all pages into a single PDF

    Parameters:
        template_path: Path to the QPT template file
        output_path: Output PDF file path
        layer_names: List of layer names to include in the legend
        logo_path: Optional logo path to override in template
        per_page: Number of layers per legend page (LEGACY PARAMETER - use max_legend_items_per_page instead)
        max_legend_items_per_page: Maximum legend items per page (new parameter)
        dpi: DPI for PDF export
        title: Title for the legend
        author: Author for the legend

    Returns:
        The output path of the generated PDF
    """
    config = LegendExportConfig(
        template_path=Path(template_path),
        output_path=Path(output_path),
        layer_names=layer_names,
        logo_path=Path(logo_path) if logo_path else None,
        max_legend_items_per_page=max_legend_items_per_page,
        dpi=dpi,
        title=title,
        author=author,
    )

    service = LegendExportService(QgsProject.instance(), config)
    return service.export()

import gc
import textwrap
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfWriter  # type:ignore
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsGraduatedSymbolRenderer,
    QgsLayerTree,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsPrintLayout,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)

from .export.pdf.common.layout_items import get_optional_item
from .export.pdf.common.metadata import apply_label_text, apply_logo
from .export.pdf.common.models import PdfExportOptions
from .export.pdf.common.pdf_export import export_layout_to_pdf
from .export.pdf.common.template_loader import create_layout_from_template
from .logger import logger
from .utils.formatting import display_date_str


@dataclass(slots=True)
class LegendExportConfig:
    """Configuration for legend export."""

    template_path: Path
    output_path: Path
    layer_names: list[str]
    logo_path: Path | None = None
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


@dataclass(slots=True)
class LegendPage:
    """Domain entity representing a legend page."""

    layer_names: list[str]
    estimated_cost: int


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

    def paginate(self, layer_names: list[str]) -> list[LegendPage]:
        """
        Paginate layers according to their legend complexity.

        Returns a list of ``LegendPage`` objects, each containing the
        layer names for that page and the total estimated cost.

        Strategy:
        - accumulate layers until max_items_per_page is reached
        - if a single layer exceeds the limit, place it alone
        """
        if not layer_names:
            raise ValueError("No layers provided for export")

        pages: list[LegendPage] = []

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

            if current_page and (current_cost + layer_cost > self.max_items_per_page):
                pages.append(LegendPage(current_page, current_cost))
                current_page = []
                current_cost = 0

            current_page.append(layer_name)
            current_cost += layer_cost

        # Final page
        if current_page:
            pages.append(LegendPage(current_page, current_cost))

        logger.info(f"Legend pagination complete: {len(pages)} page(s) generated")

        return pages


class LayoutFactory:
    """Factory for creating new layouts from templates."""

    def __init__(self, template_path: Path):
        self.template_path = template_path
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

    def create_layout(self, project: QgsProject) -> QgsPrintLayout:
        """Create a new layout from template."""
        return create_layout_from_template(
            project=project, template_path=self.template_path, layout_name="LegendLayout", register_in_manager=False
        )


class LegendLayoutBuilder:
    """Builds a single legend page layout."""

    @dataclass(slots=True)
    class LegendLayoutItems:
        """Container for layout items retrieved from the template."""

        legend: QgsLayoutItemLegend | None
        title_item: QgsLayoutItemLabel | None
        author_item: QgsLayoutItemLabel | None
        date_item: QgsLayoutItemLabel | None
        logo_item: QgsLayoutItemPicture | None
        page_item: QgsLayoutItemLabel | None

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

    def _get_layout_items(self) -> "LegendLayoutBuilder.LegendLayoutItems":
        """Retrieve and return all required layout items from the template."""
        legend = get_optional_item(self.layout, "legend", QgsLayoutItemLegend)
        title_item = get_optional_item(self.layout, "title", QgsLayoutItemLabel)
        author_item = get_optional_item(self.layout, "author", QgsLayoutItemLabel)
        date_item = get_optional_item(self.layout, "date", QgsLayoutItemLabel)
        logo_item = get_optional_item(self.layout, "logo", QgsLayoutItemPicture)
        page_item = get_optional_item(self.layout, "page", QgsLayoutItemLabel)
        return self.LegendLayoutItems(
            legend=legend,
            title_item=title_item,
            author_item=author_item,
            date_item=date_item,
            logo_item=logo_item,
            page_item=page_item,
        )

    def _format_layer_name(self, name: str, width: int = 100) -> str:
        """Wrap long layer names for legend display.

        Uses ``textwrap.wrap`` to insert line breaks so the legend
        respects the given width. Returns the formatted name.
        """
        # ``textwrap.wrap`` returns a list of lines; join with newline
        return "\n".join(textwrap.wrap(name, width=width))

    def _populate_root(self, layer_names: list[str]) -> int:
        """Add the given layers to the internal root tree.

        Returns the number of layers successfully added.
        """
        layers_added = 0
        for name in layer_names:
            layers = self.project.mapLayersByName(name)
            if not layers:
                logger.warning(f"Layer '{name}' not found in project")
                continue
            # Add the layer to the tree and capture the node
            layer_node = self.root.addLayer(layers[0])
            # Wrap long names to avoid overflow in the legend
            wrapped_name = self._format_layer_name(layer_node.name())
            layer_node.setName(wrapped_name)
            layers_added += 1
        return layers_added

    def _configure_legend(self, legend: QgsLayoutItemLegend) -> None:
        """Configure legend settings and attach the populated layer tree."""
        legend.setAutoUpdateModel(False)
        legend.model().setRootGroup(self.root)

    def _refresh_legend(self, legend: QgsLayoutItemLegend) -> None:
        """Refresh the legend to reflect the new model."""
        legend.invalidateCache()
        legend.updateLegend()
        legend.refresh()
        legend.adjustBoxSize()
        self.layout.refresh()

    def build(self, layer_names: list[str], page_number: int, total_pages: int):
        """Build the layout with given layers and metadata."""
        self.root.clear()

        items = self._get_layout_items()
        if items.legend is None:
            raise ValueError("Required legend item with ID 'legend' not found in template")

        layers_added = self._populate_root(layer_names)
        if layers_added == 0:
            raise RuntimeError(f"No valid layers found for page {page_number}")

        self._configure_legend(items.legend)
        self._refresh_legend(items.legend)

        # Setup text items
        self._setup_texts(
            items.title_item,
            items.author_item,
            items.date_item,
            items.logo_item,
            items.page_item,
            page_number,
            total_pages,
        )

    def _setup_texts(
        self,
        title_item: QgsLayoutItemLabel | None,
        author_item: QgsLayoutItemLabel | None,
        date_item: QgsLayoutItemLabel | None,
        logo_item: QgsLayoutItemPicture | None,
        page_item: QgsLayoutItemLabel | None,
        page_number: int,
        total_pages: int,
    ):
        """Setup the text items in the layout."""
        # Set up title
        apply_label_text(title_item, self.title)

        # Set up page number
        if page_item:
            page_item.setText(f"{page_number}/{total_pages}")
            page_item.setVisible(True)

        # Set up author
        apply_label_text(author_item, f"Auteur: {self.author}")

        # Set up date
        apply_label_text(date_item, display_date_str())

        # Set up logo
        apply_logo(logo_item, self.logo_path)


class PdfPageExporter:
    """Exports individual layout pages to PDF."""

    def __init__(self, config: LegendExportConfig):
        self.config = config
        if self.config.logo_path and not self.config.logo_path.exists():
            raise FileNotFoundError(f"Logo file not found: {self.config.logo_path}")

    def export(self, layout: QgsPrintLayout, output_path: Path) -> None:
        """Export layout to PDF."""
        # Create options for PDF export
        options = PdfExportOptions(
            dpi=self.config.dpi,
            write_geopdf=False,
            force_vector_output=False,
            export_layers_as_vectors=False,
            export_metadata=False,
        )

        # Use common export function
        export_layout_to_pdf(layout=layout, output_path=output_path, options=options)


class PdfMergerService:
    """Merges individual PDF pages into a single PDF."""

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

    def _export_page(self, layer_chunk: list[str], page_index: int, total_pages: int, tmp_path: Path) -> Path:
        """Create layout, build it, export to PDF and return the PDF path for a single page."""
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
        return page_path

    def export(self) -> str:
        """Execute the complete export pipeline."""
        # Paginate layers into LegendPage objects
        pages = self.paginator.paginate(self.config.layer_names)
        total_pages = len(pages)

        # Create temporary directory for page PDFs
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            page_paths = []

            # Process each page
            for page_index, page in enumerate(pages, 1):
                layer_chunk = page.layer_names
                page_path = self._export_page(layer_chunk, page_index, total_pages, tmp_path)
                page_paths.append(page_path)

            # Merge all pages
            self.merger_service.merge(page_paths, self.config.output_path)
            logger.info(f"Final legend PDF exported to: {self.config.output_path}")

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

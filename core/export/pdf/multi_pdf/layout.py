from pathlib import Path

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
)

from ....utils.formatting import display_date_str
from ..common.layout.base_layout import BasePdfLayout
from ..common.layout.items import (
    get_optional_item,
    get_required_item,
)
from ..common.layout.metadata import MetadataRenderer
from ..common.layout.metadata_items import get_metadata_layout_items
from ..common.models import LayoutMetadata
from .items import MultiPdfLayoutItems


class MultiPdfLayout(BasePdfLayout):
    """QGIS print layout builder for multi-page PDF reports.

    Extends BasePdfLayout to provide specialized functionality for creating
    multi-page PDF layouts with map items, metadata, and consistent styling.

    Handles layout creation from templates, map configuration, and metadata
    population for multi-page cartographic reports.

    Attributes:
        items: Collection of layout items (map, title, author, etc.)
    """

    def __init__(
        self,
        layout: QgsPrintLayout,
        items: MultiPdfLayoutItems,
    ) -> None:
        super().__init__(layout)

        self.items = items

    @classmethod
    def create(
        cls,
        *,
        project: QgsProject,
        template_path: Path,
    ) -> "MultiPdfLayout":
        """Create multi-PDF layout with map item extraction."""
        layout = cls.create_layout(
            project=project,
            template_path=template_path,
            layout_name="MultiPagePDF",
        )

        # Extract map-specific items
        metadata_items = get_metadata_layout_items(
            layout,
            get_optional_item,
            get_required_item,
        )
        items = MultiPdfLayoutItems(
            map_item=get_required_item(
                layout,
                "Map 1",
                QgsLayoutItemMap,
            ),
            title_item=metadata_items.title_item,
            author_item=metadata_items.author_item,
            date_item=metadata_items.date_item,
            logo_item=metadata_items.logo_item,
            page_item=get_optional_item(
                layout,
                "page",
                QgsLayoutItemLabel,
            ),
        )

        return cls(
            layout=layout,
            items=items,
        )

    @classmethod
    def create_layout(
        cls,
        *,
        project: QgsProject,
        template_path: Path,
        layout_name: str,
    ) -> QgsPrintLayout:
        """Concrete implementation required by BasePdfLayout.
        Delegates to the generic template loader.
        """

        from ..common.template_loader import create_layout_from_template

        return create_layout_from_template(
            project=project,
            template_path=template_path,
            layout_name=layout_name,
            register_in_manager=False,
        )

    @classmethod
    def build(
        cls,
        *,
        project: QgsProject,
        template_path: Path,
        extent_rect: QgsRectangle,
        visible_layers: list[QgsMapLayer],
        title: str,
        author: str,
        logo_path: Path | None,
    ) -> "MultiPdfLayout":
        """Build a complete MultiPdfLayout with all components configured."""
        layout = cls.create(
            project=project,
            template_path=template_path,
        )

        layout.configure_map(
            extent_rect=extent_rect,
            visible_layers=visible_layers,
        )

        layout.populate_metadata(
            title=title,
            author=author,
            logo_path=logo_path,
        )

        layout.stabilize()

        return layout

    def configure_map(
        self,
        *,
        extent_rect: QgsRectangle,
        visible_layers: list[QgsMapLayer],
    ) -> None:
        """Zoom the layout's map item to *extent_rect* and lock *visible_layers*.

        Args:
            extent_rect: Extent the map item is zoomed to.
            visible_layers: Layers shown on the map, in draw order.
        """
        self.items.map_item.zoomToExtent(extent_rect)
        self.items.map_item.setLayers(visible_layers)
        self.items.map_item.setKeepLayerSet(True)

    def populate_metadata(
        self,
        *,
        title: str,
        author: str,
        logo_path: Path | None,
    ) -> None:
        """Render title/author/date/logo metadata onto the layout.

        Args:
            title: Document title.
            author: Document author.
            logo_path: Optional path to the logo image.
        """
        metadata = LayoutMetadata(
            title=title,
            author=author,
            date_text=display_date_str(),
            logo_path=logo_path,
        )

        # Render metadata using the centralized renderer
        MetadataRenderer.render(
            layout=self.layout,
            metadata=metadata,
            metadata_items=self.items,
        )

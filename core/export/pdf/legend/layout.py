from pathlib import Path

from qgis.core import (
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsPrintLayout,
    QgsProject,
)

from ..common.layout.base_layout import BasePdfLayout
from ..common.layout.items import (
    get_optional_item,
    get_required_item,
)
from ..common.layout.metadata import MetadataRenderer
from ..common.layout.metadata_items import get_metadata_layout_items
from ..common.models import LayoutMetadata
from .items import LegendLayoutItems
from .legend_tree import configure_legend


class LegendLayout(BasePdfLayout):
    def __init__(
        self,
        layout: QgsPrintLayout,
        items: LegendLayoutItems,
    ) -> None:
        super().__init__(layout)

        self.items = items

    @classmethod
    def create(
        cls,
        *,
        project: QgsProject,
        template_path: Path,
        page_number: int,
    ) -> "LegendLayout":
        """Create legend layout with specific legend item extraction."""
        layout = cls.create_layout(
            project=project,
            template_path=template_path,
            layout_name=f"Legend_{page_number}",
        )

        # Extract legend-specific items
        metadata_items = get_metadata_layout_items(
            layout,
            get_optional_item,
            get_required_item,
        )
        items = LegendLayoutItems(
            legend=get_required_item(
                layout,
                "legend",
                QgsLayoutItemLegend,
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

    def configure(
        self,
        *,
        project: QgsProject,
        layer_names: list[str],
    ) -> None:
        configure_legend(
            legend=self.items.legend,
            layout=self.layout,
            project=project,
            layer_names=layer_names,
        )

    @classmethod
    def build(
        cls,
        *,
        project: QgsProject,
        template_path: Path,
        metadata: LayoutMetadata,
        layer_names: list[str],
        page_number: int,
        total_pages: int,
    ) -> "LegendLayout":
        layout = cls.create(
            project=project,
            template_path=template_path,
            page_number=page_number,
        )

        layout.configure(
            project=project,
            layer_names=layer_names,
        )

        layout.populate_metadata(
            metadata=metadata,
            page_number=page_number,
            total_pages=total_pages,
        )

        layout.stabilize()

        return layout

    def populate_metadata(
        self,
        *,
        metadata: LayoutMetadata,
        page_number: int,
        total_pages: int,
    ) -> None:
        # Render metadata using the centralized renderer
        MetadataRenderer.render(
            layout=self.layout,
            metadata=metadata,
            metadata_items=self.items,
        )

        if self.items.page_item:
            self.items.page_item.setText(f"{page_number}/{total_pages}")
            self.items.page_item.refresh()

from pathlib import Path

from qgis.core import (
    QgsPrintLayout,
    QgsProject,
)

from ....utils.formatting import display_date_str
from ..common.layout.metadata import inject_basic_metadata
from ..common.template_loader import create_layout_from_template
from .items import (
    LegendLayoutItems,
    resolve_layout_items,
)
from .legend_tree import configure_legend


def _populate_metadata(
    items: LegendLayoutItems,
    *,
    title: str,
    author: str,
    logo_path: Path | None,
    page_number: int,
    total_pages: int,
) -> None:
    from ..common.models import LayoutMetadata

    inject_basic_metadata(
        title_item=items.title_item,
        author_item=items.author_item,
        date_item=items.date_item,
        logo_item=items.logo_item,
        metadata=LayoutMetadata(
            title=title,
            author=author,
            date_text=display_date_str(),
            logo_path=logo_path,
        ),
    )
    if items.page_item:
        items.page_item.setText(f"{page_number}/{total_pages}")
        items.page_item.refresh()


def build_legend_layout(
    *,
    project: QgsProject,
    template_path: Path,
    layer_names: list[str],
    title: str,
    author: str,
    logo_path: Path | None,
    page_number: int,
    total_pages: int,
) -> QgsPrintLayout:
    layout = create_layout_from_template(
        project=project,
        template_path=template_path,
        layout_name=f"Legend_{page_number}",
        register_in_manager=False,
    )

    items = resolve_layout_items(layout)

    # Configure legend with a fresh tree built safely
    configure_legend(
        legend=items.legend,
        project=project,
        layer_names=layer_names,
    )

    _populate_metadata(
        items,
        title=title,
        author=author,
        logo_path=logo_path,
        page_number=page_number,
        total_pages=total_pages,
    )

    from ..common.lifecycle.refresh import stabilize_layout

    stabilize_layout(layout)
    return layout

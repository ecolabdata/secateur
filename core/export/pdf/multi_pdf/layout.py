from pathlib import Path

from qgis.core import (
    QgsLayout,
    QgsMapLayer,
    QgsProject,
    QgsRectangle,
)

from ....utils.formatting import display_date_str


def build_pdf_page_layout(
    project: QgsProject,
    template_path: Path,
    extent_rect: QgsRectangle,
    visible_layers: list[QgsMapLayer],
    title: str,
    author: str,
    logo_path: str | Path | None,
) -> QgsLayout:
    """Build a multi‑page PDF layout using the common builder.

    Delegates to ``build_layout_from_template`` which handles template loading,
    metadata injection and map configuration.
    """
    from ..common.layout.builder import build_layout_from_template

    return build_layout_from_template(
        project=project,
        template_path=template_path,
        layout_name="MultiPagePDF",
        title=title,
        author=author,
        date_text=display_date_str(),
        logo_path=logo_path,
        extent_rect=extent_rect,
        visible_layers=visible_layers,
    )

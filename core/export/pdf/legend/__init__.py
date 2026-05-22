from qgis.core import QgsProject

from .config import LegendExportConfig
from .service import LegendExportService


def export_legend(
    *,
    output_path: str,
    layer_names: list[str],
    logo_path: str | None = None,
    max_legend_items_per_page: int = 20,
    dpi: int = 300,
    title: str = "Légende",
    author: str = "QGIS User",
) -> str:
    """Compatibility wrapper for legend export.

    Creates a :class:`LegendExportConfig` with defaults, then runs the
    :class:`LegendExportService`.
    """
    config = LegendExportConfig.default(
        output_path=output_path,
        layer_names=layer_names,
        title=title,
        author=author,
        logo_path=logo_path,
        max_legend_items_per_page=max_legend_items_per_page,
    )
    config.dpi = dpi

    service = LegendExportService(
        QgsProject.instance(),
        config,
    )
    return service.export()

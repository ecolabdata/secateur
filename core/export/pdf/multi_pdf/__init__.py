"""
Multi-Page PDF Export module.

This is the facade for the new multi-page PDF export functionality, providing a clean
interface while delegating to the new modular structure.
"""

from qgis.core import QgsMapLayer, QgsProcessingFeedback, QgsProject

from .config import MultiPagePdfExportConfig
from .service import MultiPagePdfExportService


def export_results_to_multi_page_pdf(
    result_layers: list[QgsMapLayer],
    output_path: str,
    logo_path: str,
    basemap_layer: QgsMapLayer | None = None,
    author: str = "DDT",
    title: str = "Résultats Secateur",
    feedback: QgsProcessingFeedback | None = None,
) -> str:
    config = MultiPagePdfExportConfig.default(
        output_path=output_path,
        title=title,
        author=author,
        logo_path=logo_path,
    ).with_export_params(
        result_layers=result_layers,
        basemap_layer=basemap_layer,
        feedback=feedback,
    )

    service = MultiPagePdfExportService(
        QgsProject.instance(),
        config,
    )

    # Call the base class export method which handles the common logic
    return service.export()

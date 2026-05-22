"""
GeoPDF Export module.

This is the facade for the new GeoPDF export functionality, providing a clean
interface while delegating to the new modular structure.
"""

from qgis.core import QgsMapLayer, QgsProcessingFeedback, QgsProject

from .config import GeoPdfExportConfig
from .service import GeoPdfExportService


def export_results_to_pdf(
    result_layers: list[QgsMapLayer],
    output_path: str,
    logo_path: str,
    basemap_layer: QgsMapLayer | None = None,
    author: str = "DDT",
    title: str = "Résultats Secateur",
    feedback: QgsProcessingFeedback | None = None,
) -> str:
    """
    Export results to GeoPDF using the new modular structure.

    This function serves as a facade that provides backward compatibility
    while using the new modular architecture.

    Args:
        result_layers: List of layers to include in the export
        output_path: Output path for the PDF file
        logo_path: Path to the logo to include in the report
        basemap_layer: Optional basemap layer to include
        author: Author name to include in the report
        title: Title to include in the report

    Returns:
        The path to the exported PDF file
    """
    # Create configuration object using default helper
    config = GeoPdfExportConfig.default(
        output_path=output_path,
        title=title,
        author=author,
        logo_path=logo_path,
        export_legend=True,
    )

    # Create service and export
    service = GeoPdfExportService(QgsProject.instance(), config)
    return service.export(result_layers, basemap_layer, feedback)

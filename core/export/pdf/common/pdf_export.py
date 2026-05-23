"""
Common PDF export utilities for PDF export.
"""

from contextlib import suppress
from pathlib import Path

from qgis.core import QgsLayout, QgsLayoutExporter

from .models import PdfExportOptions


def build_pdf_export_settings(
    options: PdfExportOptions,
) -> QgsLayoutExporter.PdfExportSettings:
    """Build PDF export settings from options."""
    settings = QgsLayoutExporter.PdfExportSettings()
    settings.dpi = options.dpi
    settings.writeGeoPdf = options.write_geopdf
    settings.forceVectorOutput = options.force_vector_output
    settings.exportLayersAsVectors = options.export_layers_as_vectors
    settings.exportMetadata = options.export_metadata
    return settings


def export_layout_to_pdf(
    *,
    layout: QgsLayout,
    output_path: Path,
    options: PdfExportOptions,
) -> Path:
    """Export a layout to PDF using the given options."""
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean previous file if present
    if output_path.is_file():
        with suppress(Exception):
            output_path.unlink()

    # Validate extension
    if output_path.suffix.lower() != ".pdf":
        raise ValueError(f"Invalid output file extension: {output_path.suffix}")

    # Write permission test (basic check)
    test_file = output_path.parent / ".__kilo_write_test"
    try:
        with open(test_file, "w") as f:
            f.write("test")
        test_file.unlink()
    except Exception:
        pass  # Silently ignore permission test errors

    exporter = QgsLayoutExporter(layout)
    settings = build_pdf_export_settings(options)

    # Centralized layout stabilization and Qt event processing
    from .lifecycle.refresh import stabilize_layout

    stabilize_layout(layout)

    if len(layout.items()) == 0:
        raise RuntimeError("Layout contains no items; template may have failed to load.")

    result = exporter.exportToPdf(str(output_path), settings)
    # Retry without GeoPDF flag if needed (code 4)
    if result != QgsLayoutExporter.Success and result == 4:
        settings.writeGeoPdf = False
        result = exporter.exportToPdf(str(output_path), settings)

    # Perform deterministic cleanup after export
    from .lifecycle.cleanup import finalize_export_cycle

    finalize_export_cycle()
    if result != QgsLayoutExporter.Success:
        error_msg = exporter.errorMessage() if hasattr(exporter, "errorMessage") else ""
        error_file = exporter.errorFile() if hasattr(exporter, "errorFile") else ""
        raise RuntimeError(f"PDF export failed with code: {result}. Details: {error_msg} File: {error_file}")

    return output_path

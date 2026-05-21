"""
Infrastructure class handling the heavy GeoPDF export logic.
It encapsulates QGIS‑specific, IO‑heavy operations such as retry handling,
processEvents, permission checks and error message extraction.
The service layer should only orchestrate and not be aware of these details.
"""

from pathlib import Path

from qgis.core import QgsLayout, QgsLayoutExporter

from ...logger import logger
from ...utils.layouts import clean_layouts


class GeoPdfExporter:
    """Export a QgsLayout to a GeoPDF file.

    The method performs the actual export, handling retries, permission checks,
    and QGIS event processing. It returns the path of the generated file.
    """

    def export(self, layout: "QgsLayout", output_path: Path, settings: "QgsLayoutExporter.PdfExportSettings") -> Path:
        """Export the given layout to *output_path* using *settings*.

        Args:
            layout: The QGIS layout to export.
            output_path: Destination file path (must end with .pdf).
            settings: PDF export settings configured by the caller.
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Clean previous file if present
        if output_path.is_file():
            try:
                output_path.unlink()
                logger.debug(f"Removed existing PDF file: {output_path}")
            except Exception as rm_err:
                logger.warning(f"Could not remove existing PDF file {output_path}: {rm_err}")

        # Validate extension
        if output_path.suffix.lower() != ".pdf":
            logger.error(f"Invalid output file extension: {output_path.suffix}")

        # Write permission test
        test_file = output_path.parent / ".__kilo_write_test"
        try:
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()
            logger.debug("Write permission test succeeded.")
        except Exception as wf_err:
            logger.error(f"Write permission test failed: {wf_err}")

        exporter = QgsLayoutExporter(layout)
        try:
            # Refresh layout
            layout.refresh()
            exporter.layout().refresh()

            # Process Qt events
            from qgis.PyQt.QtWidgets import QApplication

            QApplication.processEvents()

            if len(layout.items()) == 0:
                raise RuntimeError("Layout contains no items; template may have failed to load.")

            result = exporter.exportToPdf(str(output_path), settings)
            # Retry without GeoPDF flag if needed (code 4)
            if result != QgsLayoutExporter.Success and result == 4:
                logger.debug("Initial GeoPDF export failed with code 4; retrying without GeoPDF flag.")
                settings.writeGeoPdf = False
                result = exporter.exportToPdf(str(output_path), settings)

            QApplication.processEvents()
            if result != QgsLayoutExporter.Success:
                error_msg = exporter.errorMessage() if hasattr(exporter, "errorMessage") else ""
                error_file = exporter.errorFile() if hasattr(exporter, "errorFile") else ""
                raise RuntimeError(f"PDF export failed with code: {result}. Details: {error_msg} File: {error_file}")

            logger.info(f"GeoPDF exported to: {output_path}")
            return output_path
        finally:
            # Clean temporary layout artefacts if possible
            manager = layout.project().layoutManager() if hasattr(layout, "project") else None
            if manager:
                clean_layouts(manager)

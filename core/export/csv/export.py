import csv
import os
from contextlib import contextmanager

from qgis.core import (
    QgsMapLayer,
    QgsProcessingFeedback,
    QgsVectorLayer,
)

from ...utils.layers import iterate_layers
from ...utils.formatting import _safe_filename, _format_value

def export_results_to_csv(
    result_layers: list[QgsMapLayer],
    output_dir: str,
    feedback: QgsProcessingFeedback | None = None,
) -> list[str]:
    """Export each result layer as a separate CSV file inside output_dir.

    Creates output_dir if it doesn't exist. Returns the list of written file paths.
    progress.update(current, total, name) is called before each layer if a progress object is provided.
    """
    os.makedirs(output_dir, exist_ok=True)

    written = []

    def _write_csv(layer: QgsVectorLayer):
        """Callback used by :func:`iterate_layers` to write one CSV file.

        Non-vector layers are ignored.
        """
        if not isinstance(layer, QgsVectorLayer):
            return
        filename = _safe_filename(layer.name()) + ".csv"
        filepath = os.path.join(output_dir, filename)

        field_names = [field.name() for field in layer.fields()]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(field_names)
            for feat in layer.getFeatures():
                writer.writerow([_format_value(v) for v in feat.attributes()])

        written.append(filepath)

    iterate_layers(result_layers, _write_csv, feedback)
    # Ensure UI remains responsive during export
    from qgis.PyQt.QtWidgets import QApplication

    QApplication.processEvents()

    return written
"""
Extent calculation utilities shared across PDF exporters.
"""

from qgis.core import QgsMapLayer, QgsRectangle, QgsVectorLayer


def get_source_vector_layer(result_layers: list[QgsMapLayer]) -> QgsVectorLayer:
    """Validate *result_layers* for PDF export.

    Raises ``ValueError`` if the list is empty and ``TypeError`` if the first
    element is not a ``QgsVectorLayer``.
    """
    if not result_layers:
        raise ValueError("result_layers must contain at least one layer for extent calculation")

    layer = result_layers[0]

    if not isinstance(layer, QgsVectorLayer):
        raise TypeError("First result layer must be a vector layer")

    return layer


def compute_export_extent(layer: QgsVectorLayer) -> QgsRectangle:
    """Return a buffered ``QgsRectangle`` covering *layer*.

    The rectangle is enlarged by 5 % of its width and height.
    """
    bbox = layer.extent()
    bbox.grow(bbox.width() * 0.05 + bbox.height() * 0.05)
    return QgsRectangle(bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum())

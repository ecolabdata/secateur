from qgis.core import (
    QgsMapLayer,
    QgsProject,
    QgsVectorLayer,
)

from ..utils.layers import get_results_group


def apply_layer_presentation(
    result_layer: QgsMapLayer,
    original_layer: QgsMapLayer,
) -> None:
    """Apply the rendering and naming of the result layer."""
    result_layer.setName(original_layer.name())
    if isinstance(result_layer, QgsVectorLayer) and isinstance(original_layer, QgsVectorLayer):
        result_layer.setRenderer(original_layer.renderer().clone())


def add_results_to_project(result_layers: list[QgsMapLayer]):
    project = QgsProject.instance()
    if project is None:
        return

    group = get_results_group(clear=True)
    if group is None:
        # If the results group cannot be created, abort adding layers to it.
        # Layers are still added to the project (visible in the layer list).
        for layer in result_layers:
            project.addMapLayer(layer, False)
        return
    for layer in result_layers:
        project.addMapLayer(layer, False)
        group.addLayer(layer)  # type: ignore

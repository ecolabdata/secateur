from qgis.core import (
    QgsMapLayer,
    QgsProject,
    QgsVectorLayer,
)


class LayerResolver:
    """Resolve QGIS map layers by ID from the current project."""

    @staticmethod
    def get(layer_id: str) -> QgsMapLayer | None:
        """Return the layer with *layer_id*, or ``None`` if not found."""
        if not layer_id:
            return None

        return QgsProject.instance().mapLayer(layer_id)

    @staticmethod
    def get_vector(layer_id: str) -> QgsVectorLayer | None:
        """Return the layer with *layer_id* if it is a ``QgsVectorLayer``, else ``None``."""
        layer = LayerResolver.get(layer_id)

        if isinstance(layer, QgsVectorLayer):
            return layer

        return None

    @staticmethod
    def get_many(layer_ids: list[str]) -> list[QgsMapLayer]:
        """Return the layers matching *layer_ids*, skipping any that are not found."""
        return [layer for lid in layer_ids if (layer := LayerResolver.get(lid)) is not None]

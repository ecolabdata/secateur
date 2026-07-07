from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

import processing  # type: ignore
from qgis.core import (
    QgsFeature,
    QgsFillSymbol,
    QgsMapLayer,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from ..core.constants import BASEMAP_GROUP_NAME, CREATED_OBJECTS_GROUP_NAME, RESULT_GROUP_NAME
from ..core.intersection.intersection_context import (
    build_intersection_context,
    filter_layers_by_extent,
)
from ..core.intersection.intersection_metrics import _format_metrics_summary
from ..core.intersection.intersection_processing import intersect_layers, prepare_layers
from ..core.intersection.intersection_results import add_results_to_project
from ..core.utils.layer_resolver import LayerResolver
from ..core.utils.layers import find_group, find_layers, find_tree_layer, get_created_objects_group, get_results_group
from ..core.utils.visibility import set_layer_visible
from .settings import SettingsManager

# ──────────────────────────────────────────────
#  Service result objects (explicit contracts)
# ──────────────────────────────────────────────
Level = Literal["info", "warning", "error"]


@dataclass
class SelectionResult:
    """Outcome of a selection attempt, with a status message for the UI."""

    layer: QgsVectorLayer | None
    feature: QgsFeature | None
    message: str
    level: Level

    def __post_init__(self):
        assert self.level in ("info", "warning", "error")
        if self.layer is not None:
            assert isinstance(self.layer, QgsVectorLayer)
        if self.feature is not None:
            assert isinstance(self.feature, QgsFeature)


@dataclass
class ProcessResult:
    """Outcome of an intersection run, with a status message for the UI."""

    result_layer_ids: list[str]
    message: str
    level: Level

    def __post_init__(self):
        assert isinstance(self.result_layer_ids, list)
        assert all(isinstance(x, str) for x in self.result_layer_ids)


# ──────────────────────────────────────────────
#  SecateurService (NO UI)
# ──────────────────────────────────────────────


@runtime_checkable
class QgisInterfaceProtocol(Protocol):
    """Subset of QGIS's ``iface`` used by the service, for typing and testability."""

    def activeLayer(self) -> QgsMapLayer | None:
        """Return the currently active map layer, or ``None``."""
        ...


class SecateurService:
    """Business logic service.

    Contains NO UI (Qt) dependency. Preserves all existing QGIS side effects.
    """

    def __init__(self) -> None:
        self.settings = SettingsManager()

    # ──────────────────────────────────────────────
    #  Selection
    # ──────────────────────────────────────────────

    def select(self, iface: QgisInterfaceProtocol) -> SelectionResult:
        """Validate the active layer/feature selection and prepare it for processing.

        Rejects layers that are not vector layers or that belong to the
        results group, and materializes a single selected feature into a
        memory layer under the "created objects" group.

        Args:
            iface: QGIS interface used to read the active layer.

        Returns:
            A ``SelectionResult`` describing the outcome, with a status
            message and level for display in the UI.
        """
        layer = iface.activeLayer()

        if layer is None:
            return SelectionResult(None, None, "Aucune entité active.", "warning")

        if not isinstance(layer, QgsVectorLayer):
            return SelectionResult(None, None, "Sélection réinitialisée (pas de couche vectorielle).", "warning")

        results_group = get_results_group()
        if results_group is None:
            return SelectionResult(None, None, f"Impossible d'accéder au groupe {RESULT_GROUP_NAME}.", "error")

        if find_tree_layer(results_group, layer) is not None:
            return SelectionResult(None, None, f"La sélection appartient au groupe {RESULT_GROUP_NAME}.", "warning")

        selected = layer.selectedFeatures()

        if len(selected) == 1:
            return self._select_single_feature(layer, selected[0])

        if len(selected) > 1:
            return SelectionResult(layer, None, "Plusieurs objets sélectionnés !", "warning")

        return SelectionResult(layer, None, f"Couche sélectionnée : {layer.name()}", "info")

    def _select_single_feature(self, layer: QgsVectorLayer, feature: QgsFeature) -> SelectionResult:
        mem_layer = self._create_memory_layer_from_feature(layer, feature, hide_source=True)

        group = get_created_objects_group()
        if group is None:
            return SelectionResult(
                mem_layer,
                feature,
                f"Impossible d'ajouter la couche : groupe '{CREATED_OBJECTS_GROUP_NAME}' introuvable.",
                "error",
            )

        group.insertLayer(-1, mem_layer)
        return SelectionResult(mem_layer, feature, "", "info")

    # ──────────────────────────────────────────────
    #  Process
    # ──────────────────────────────────────────────

    def run(self, selected_layer_id: str, feedback: QgsProcessingFeedback) -> ProcessResult:
        """Run the intersection between the selected layer and visible project layers.

        Args:
            selected_layer_id: ID of the reference vector layer.
            feedback: Feedback object used to report progress and warnings.

        Returns:
            A ``ProcessResult`` with the IDs of the created result layers
            and a status message/level for display in the UI.
        """
        selected_layer = LayerResolver.get_vector(selected_layer_id)

        if selected_layer is None:
            return ProcessResult(
                [],
                "La couche sélectionnée est introuvable.",
                "error",
            )

        include_raster = self.settings.include_raster

        group = get_results_group(clear=True)
        if group is None:
            return ProcessResult([], "Impossible d'accéder au groupe 'Résultats secateur'.", "error")

        context = build_intersection_context(selected_layer, include_raster=include_raster)

        allowed_types = (QgsVectorLayer, QgsRasterLayer) if self.settings.include_raster else (QgsVectorLayer,)
        layers = find_layers(exclude=selected_layer, allowed_types=allowed_types)

        # Exclude layers from BASEMAP_GROUP_NAME
        basemap_group = find_group([BASEMAP_GROUP_NAME])
        if basemap_group is not None:
            layers = [layer for layer in layers if find_tree_layer(basemap_group, layer) is None]

        layers = filter_layers_by_extent(
            context,
            layers,
        )
        if not layers:
            return ProcessResult([], "Aucune couche visible à comparer.", "error")

        prepared_layers = prepare_layers(layers, context, feedback)
        results = intersect_layers(selected_layer, prepared_layers, context=context, feedback=feedback)

        if results:
            add_results_to_project(results)

            self._cleanup_created_objects_group()

            result_ids = [layer.id() for layer in results]
            layer_count = max(len(results) - 1, 0)

            # Display metrics summary if available
            if context.metrics.layers:
                metrics_msg = _format_metrics_summary(context.metrics)
                feedback.pushInfo(metrics_msg)

            return ProcessResult(result_ids, f"{layer_count} couches trouvées.", "info")

        return ProcessResult([], "Aucun résultat.", "info")

    def _cleanup_created_objects_group(self):
        objs_group = get_created_objects_group(clear=True)
        if objs_group is not None:
            QgsProject.instance().layerTreeRoot().removeChildNode(objs_group)

    # ──────────────────────────────────────────────
    #  Memory layer
    # ──────────────────────────────────────────────

    def _create_memory_layer_from_feature(
        self,
        source_layer: QgsVectorLayer,
        feature: QgsFeature,
        hide_source: bool = False,
    ) -> QgsVectorLayer:
        layer_name = f"{source_layer.name()}_feature_{feature.id()}"
        project = QgsProject.instance()

        for lyr in project.mapLayersByName(layer_name):
            project.removeMapLayer(lyr)

        geom_type = QgsWkbTypes.displayString(source_layer.wkbType())
        mem_layer = QgsVectorLayer(
            f"{geom_type}?crs={source_layer.crs().authid()}",
            layer_name,
            "memory",
        )

        mem_layer.dataProvider().addAttributes(source_layer.fields())
        mem_layer.updateFields()

        new_feat = QgsFeature()
        new_feat.setGeometry(feature.geometry())
        new_feat.setAttributes(feature.attributes())
        mem_layer.dataProvider().addFeature(new_feat)
        mem_layer.updateExtents()

        processing.run(
            "native:createspatialindex",
            {
                "INPUT": mem_layer,
            },
        )

        symbol = QgsFillSymbol.createSimple(
            {
                "color": "0,0,0,0",  # RDGBA=0 for transparency
                "outline_color": "255,0,0",  # red
                "outline_width": "0.6",
            }
        )
        # 65% opacity
        symbol.setOpacity(0.35)
        mem_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        mem_layer.triggerRepaint()

        project.addMapLayer(mem_layer, False)

        if hide_source:
            set_layer_visible(project.layerTreeRoot(), source_layer, False)

        return mem_layer

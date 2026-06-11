from contextlib import suppress

import processing  # type: ignore
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeatureRequest,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from ..utils.feedback import report_layer_metrics
from ..utils.layers import filter_out_source, get_results_group
from .intersection_context import IntersectionContext, get_source_extent_in_crs
from .profiling import timed_call

# ──────────────────────────────────────────────
#  LAYERS
# ──────────────────────────────────────────────


def _reproject_layer(
    layer: QgsVectorLayer | QgsRasterLayer,
    target_crs: QgsCoordinateReferenceSystem,
    feedback: QgsProcessingFeedback | None = None,
    context: QgsProcessingContext | None = None,
) -> QgsVectorLayer | QgsRasterLayer:
    """
    Reprojette une couche (vecteur ou raster) vers target_crs.
    Retourne une couche en mémoire (memory) avec le CRS cible.
    """
    if layer.crs() == target_crs:
        return layer

    context = context or QgsProcessingContext()
    feedback = feedback or QgsProcessingFeedback()

    # --- VECTEUR ---
    if isinstance(layer, QgsVectorLayer):
        params = {"INPUT": layer, "TARGET_CRS": target_crs.toWkt(), "OUTPUT": "memory:"}
        result = processing.run("native:reprojectlayer", params, context=context, feedback=feedback)
        reprojected_layer = result["OUTPUT"]
        if isinstance(reprojected_layer, QgsVectorLayer):
            reprojected_layer.setName(layer.name() + "_reproj")
        if isinstance(reprojected_layer, str):
            reprojected_layer = QgsVectorLayer(reprojected_layer, layer.name() + "_reproj", "ogr")
        return reprojected_layer

    # --- RASTER ---
    if isinstance(layer, QgsRasterLayer):
        params = {
            "INPUT": layer.source(),
            "TARGET_CRS": target_crs.toWkt(),
            "RESAMPLING": 0,  # nearest neighbor
            "NODATA": None,
            "TARGET_RESOLUTION": None,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "TARGET_EXTENT": None,
            "TARGET_EXTENT_CRS": None,
            "MULTITHREADING": True,
            "EXTRA": "",
            "OUTPUT": "TEMPORARY_OUTPUT",
        }
        result = processing.run("gdal:warpreproject", params, context=context, feedback=feedback)
        reprojected_layer = QgsRasterLayer(result["OUTPUT"], layer.name() + "_reproj")
        return reprojected_layer

    raise ValueError(f"Unsupported layer type: {type(layer)}")


# ──────────────────────────────────────────────
#  INTERSECTION
# ──────────────────────────────────────────────
def _extract_by_location(
    input_layer: QgsVectorLayer,
    intersect_layer: QgsVectorLayer,
) -> QgsVectorLayer:
    result = processing.run(
        "native:extractbylocation",
        {
            "INPUT": input_layer,
            "PREDICATE": [0],
            "INTERSECT": intersect_layer,
            "OUTPUT": "memory:",
        },
    )

    return result["OUTPUT"]


def _fix_geometries(
    layer: QgsVectorLayer,
) -> QgsVectorLayer:
    result = processing.run(
        "native:fixgeometries",
        {
            "INPUT": layer,
            "OUTPUT": "memory:",
        },
    )

    return result["OUTPUT"]


def _extract_by_location_with_retry(
    input_layer: QgsVectorLayer,
    intersect_layer: QgsVectorLayer,
    feedback: QgsProcessingFeedback | None = None,
) -> QgsVectorLayer:
    try:
        return _extract_by_location(
            input_layer,
            intersect_layer,
        )

    except Exception:
        if feedback:
            feedback.pushWarning(f"extractbylocation a échoué sur {input_layer.name()}, tentative avec fixgeometries.")

        fixed_layer = _fix_geometries(input_layer)

        return _extract_by_location(
            fixed_layer,
            intersect_layer,
        )


def _create_spatial_subset(
    layer: QgsVectorLayer,
    context: IntersectionContext,
) -> QgsVectorLayer:
    source_extent = get_source_extent_in_crs(
        context,
        layer.crs(),
    )

    request = QgsFeatureRequest()
    request.setFilterRect(source_extent)

    materialized = layer.materialize(request)

    materialized.setName(f"{layer.name()}_subset")

    return materialized


def _has_feature_in_extent(
    layer: QgsVectorLayer,
    extent: QgsRectangle,
) -> bool:
    """Test if a layer has any features in the given extent."""
    request = QgsFeatureRequest()
    request.setFilterRect(extent)
    request.setLimit(1)

    return next(layer.getFeatures(request), None) is not None


def _has_features(
    layer: QgsVectorLayer,
) -> bool:
    return next(layer.getFeatures(), None) is not None


def intersect_layer(
    source_layer: QgsVectorLayer,
    layers: list[QgsVectorLayer | QgsRasterLayer],
    context: IntersectionContext,
    feedback: QgsProcessingFeedback | None = None,
) -> list[QgsVectorLayer]:
    results = []
    total = len(layers)
    project = QgsProject.instance()
    if project is None:
        return results

    # CRS du projet
    project_crs = project.crs()

    # Add source layer as first result
    source_layer_proj = _reproject_layer(source_layer, project_crs)
    results.append(source_layer_proj)

    # Exclude the source layer from processing
    layers = filter_out_source(layers, source_layer)
    for i, layer in enumerate(layers):
        if feedback:
            feedback.setProgress(int(i / total * 100))
            feedback.pushInfo(f"[{i + 1}/{total}] {layer.name()}")

        if not isinstance(layer, QgsVectorLayer):
            continue

        # Check if layer has features in the source extent before creating subset
        source_extent = get_source_extent_in_crs(
            context,
            layer.crs(),
        )

        if not _has_feature_in_extent(layer, source_extent):
            continue

        # Reproject overlay to project CRS
        subset_layer, bbox_time = timed_call(
            _create_spatial_subset,
            layer,
            context,
        )

        if feedback:
            # Store metrics
            layer_metrics = context.metrics.get_layer_metrics(layer.name())
            layer_metrics.bbox_seconds = bbox_time
            #
            count = subset_layer.featureCount()
            feedback.pushInfo(f"{layer.name()} subset_count={count}")

        if not _has_features(subset_layer):
            continue

        overlay_for_query, reproj_time = timed_call(
            _reproject_layer,
            subset_layer,
            project_crs,
        )

        processing.run(
            "native:createspatialindex",
            {
                "INPUT": overlay_for_query,
            },
        )

        if feedback:
            # Store metrics
            layer_metrics = context.metrics.get_layer_metrics(layer.name())
            layer_metrics.reproj_seconds = reproj_time

        mem_layer, extract_time = timed_call(
            _extract_by_location_with_retry,
            overlay_for_query,
            source_layer_proj,
            feedback,
        )

        if feedback:
            # Store metrics
            layer_metrics = context.metrics.get_layer_metrics(layer.name())
            layer_metrics.extract_seconds = extract_time

            # Report metrics and warnings
            report_layer_metrics(feedback, layer.name(), layer_metrics)

        mem_layer.setName(layer.name())
        with suppress(Exception):
            mem_layer.setRenderer(layer.renderer().clone())

        if _has_features(mem_layer):
            results.append(mem_layer)

    return results


# ──────────────────────────────────────────────
#  PROJECT
# ──────────────────────────────────────────────


def add_results_to_project(result_layers: list[QgsVectorLayer]):
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

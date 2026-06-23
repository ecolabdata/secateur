from dataclasses import dataclass

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeatureRequest,
    QgsMapLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from ..utils.feedback import report_layer_metrics
from .intersection_context import IntersectionExecutionContext, get_source_extent_in_crs
from .intersection_results import apply_layer_presentation
from .profiling import timed_call


@dataclass(slots=True)
class PreparedLayer:
    source_layer: QgsVectorLayer | QgsRasterLayer
    working_layer: QgsVectorLayer | QgsRasterLayer


def prepare_layers(
    layers: list[QgsVectorLayer | QgsRasterLayer],
    context: IntersectionExecutionContext,
    feedback: QgsProcessingFeedback | None = None,
) -> list[PreparedLayer]:
    """
    Préparer les couches prêtes à être traitées.
    """
    prepared_layers = []

    for layer in layers:
        if isinstance(layer, QgsVectorLayer):
            prepared_layer = _prepare_vector_layer(layer, context, feedback)
            if prepared_layer is not None:
                prepared_layers.append(prepared_layer)
        elif isinstance(layer, QgsRasterLayer):
            prepared_layer = _prepare_raster_layer(layer, context)
            prepared_layers.append(prepared_layer)

    return prepared_layers


def _prepare_vector_layer(
    layer: QgsVectorLayer,
    context: IntersectionExecutionContext,
    feedback: QgsProcessingFeedback | None = None,
) -> PreparedLayer | None:
    """
    Préparer une couche vectorielle pour l'intersection.
    """
    # Create spatial subset (bbox timing)
    subset_layer, bbox_time = timed_call(_create_spatial_subset, layer, context)

    # Record bbox timing
    layer_metrics = context.metrics.get_layer_metrics(layer.name())
    layer_metrics.bbox_seconds = bbox_time

    # Check if subset is empty
    source_extent = get_source_extent_in_crs(context, layer.crs())
    if not _has_feature_in_extent(subset_layer, source_extent):
        return None

    # Reproject if needed (reproj timing)
    project = QgsProject.instance()
    if project is None:
        return None

    project_crs = project.crs()
    if layer.crs() != project_crs:
        reprojected_layer, reproj_time = timed_call(_reproject_layer, subset_layer, project_crs)
        layer_metrics.reproj_seconds = reproj_time
        return PreparedLayer(source_layer=layer, working_layer=reprojected_layer)
    else:
        # No reprojection performed
        layer_metrics.reproj_seconds = 0.0
        return PreparedLayer(source_layer=layer, working_layer=subset_layer)


def _prepare_raster_layer(
    layer: QgsRasterLayer,
    context: IntersectionExecutionContext,
) -> PreparedLayer:
    """
    Préparer une couche raster pour l'intersection.
    """
    return PreparedLayer(source_layer=layer, working_layer=layer)


def _create_spatial_subset(
    layer: QgsVectorLayer,
    context: IntersectionExecutionContext,
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
        import processing  # type: ignore

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
        import processing  # type: ignore

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


def _extract_by_location(
    input_layer: QgsVectorLayer,
    intersect_layer: QgsVectorLayer,
) -> QgsVectorLayer:
    import processing  # type: ignore

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
    import processing  # type: ignore

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


def _has_features(
    layer: QgsVectorLayer,
) -> bool:
    return next(layer.getFeatures(), None) is not None


def intersect_layers(
    source_layer: QgsVectorLayer,
    prepared_layers: list[PreparedLayer],
    context: IntersectionExecutionContext,
    feedback: QgsProcessingFeedback | None = None,
) -> list[QgsMapLayer]:
    """
    Calcul d'intersection uniquement.
    """
    results = []
    project = QgsProject.instance()
    if project is None:
        return results

    # Add source layer as first result
    project_crs = project.crs()
    source_layer_proj = _reproject_layer(source_layer, project_crs)
    # Apply style from original source layer to the reprojected source result
    apply_layer_presentation(source_layer_proj, source_layer)
    results.append(source_layer_proj)

    for prepared_layer in prepared_layers:
        working_layer = prepared_layer.working_layer

        if isinstance(working_layer, QgsVectorLayer):
            # Vector layer processing
            if not _has_features(working_layer):
                continue

            # Extract by location with timing
            extracted_layer, extract_time = timed_call(
                _extract_by_location_with_retry,
                working_layer,
                source_layer_proj,
                feedback,
            )
            # Record extract timing
            layer_metrics = context.metrics.get_layer_metrics(working_layer.name())
            layer_metrics.extract_seconds = extract_time

            if _has_features(extracted_layer):
                apply_layer_presentation(extracted_layer, prepared_layer.source_layer)
                results.append(extracted_layer)
                # Report metrics if feedback available
                if feedback:
                    report_layer_metrics(feedback, working_layer.name(), layer_metrics)

        elif isinstance(working_layer, QgsRasterLayer):
            # Raster layer processing - just clone and add
            cloned_layer = clone_raster_layer(
                prepared_layer.source_layer,
            )

            apply_layer_presentation(
                cloned_layer,
                prepared_layer.source_layer,
            )

            results.append(cloned_layer)

    return results


def clone_raster_layer(
    layer: QgsRasterLayer,
) -> QgsRasterLayer:
    """
    Clone a raster layer to create a new instance with the same properties.
    """
    clone = QgsRasterLayer(
        layer.source(),
        layer.name(),
        layer.providerType(),
    )
    clone.setOpacity(layer.renderer().opacity())
    return clone

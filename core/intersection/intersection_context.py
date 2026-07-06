from dataclasses import dataclass, field

from qgis.core import (
    # existing imports
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from .intersection_metrics import IntersectionMetrics


@dataclass(slots=True)
class IntersectionExecutionContext:
    """Data computed once for the whole analysis."""

    source_crs: QgsCoordinateReferenceSystem
    source_extent: QgsRectangle

    include_raster: bool = False

    # Holds performance metrics for the intersection process
    metrics: IntersectionMetrics = field(default_factory=IntersectionMetrics)

    transform_cache: "TransformCache" = field(default_factory=lambda: TransformCache())

    extent_cache: dict[str, QgsRectangle] = field(default_factory=dict)


def get_source_extent_in_crs(
    context: IntersectionExecutionContext,
    target_crs: QgsCoordinateReferenceSystem,
) -> QgsRectangle:
    """Return the source extent reprojected to *target_crs*, using the cache.

    Args:
        context: Execution context holding the source extent and caches.
        target_crs: CRS to reproject the source extent to.

    Returns:
        The source extent in *target_crs*.
    """
    if target_crs == context.source_crs:
        return context.source_extent

    key = target_crs.authid()

    cached = context.extent_cache.get(key)

    if cached is not None:
        return cached

    transform = context.transform_cache.get(
        context.source_crs,
        target_crs,
    )

    extent = transform.transformBoundingBox(context.source_extent)

    context.extent_cache[key] = extent

    return extent


def build_intersection_context(
    source_layer: QgsVectorLayer,
    *,
    include_raster: bool = False,
) -> IntersectionExecutionContext:
    """Build all the reusable information related to the source layer."""

    return IntersectionExecutionContext(
        source_crs=source_layer.crs(),
        source_extent=source_layer.extent(),
        include_raster=include_raster,
    )


@dataclass(slots=True)
class TransformCache:
    """Cache of ``QgsCoordinateTransform`` instances keyed by CRS pair."""

    _cache: dict[
        tuple[str, str],
        QgsCoordinateTransform,
    ] = field(default_factory=dict)

    def get(
        self,
        source_crs: QgsCoordinateReferenceSystem,
        target_crs: QgsCoordinateReferenceSystem,
    ) -> QgsCoordinateTransform:
        """Return the cached transform for (*source_crs*, *target_crs*), creating it if needed."""
        key = (
            source_crs.authid(),
            target_crs.authid(),
        )

        transform = self._cache.get(key)

        if transform is None:
            transform = QgsCoordinateTransform(
                source_crs,
                target_crs,
                QgsProject.instance(),
            )

            self._cache[key] = transform

        return transform


def may_intersect_source(
    context: IntersectionExecutionContext,
    layer: QgsVectorLayer | QgsRasterLayer,
) -> bool:
    """Quick bounding-box intersection test."""

    candidate_extent = layer.extent()

    candidate_crs = layer.crs()

    if candidate_crs != context.source_crs:
        transform = context.transform_cache.get(
            candidate_crs,
            context.source_crs,
        )

        candidate_extent = transform.transformBoundingBox(candidate_extent)

    return context.source_extent.intersects(candidate_extent)


def filter_layers_by_extent(
    context: IntersectionExecutionContext,
    layers: list[QgsVectorLayer | QgsRasterLayer],
) -> list[QgsVectorLayer | QgsRasterLayer]:
    """Return the subset of *layers* whose extent may intersect the source layer."""
    return [layer for layer in layers if may_intersect_source(context, layer)]

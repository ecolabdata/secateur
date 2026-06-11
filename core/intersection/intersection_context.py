from dataclasses import dataclass, field

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from .intersection_metrics import IntersectionMetrics


@dataclass(slots=True)
class IntersectionContext:
    """
    Données calculées une seule fois pour toute l'analyse.
    """

    source_crs: QgsCoordinateReferenceSystem
    source_extent: QgsRectangle

    transform_cache: "TransformCache" = field(default_factory=lambda: TransformCache())

    extent_cache: dict[str, QgsRectangle] = field(default_factory=dict)

    metrics: IntersectionMetrics = field(default_factory=IntersectionMetrics)


def get_source_extent_in_crs(
    context: IntersectionContext,
    target_crs: QgsCoordinateReferenceSystem,
) -> QgsRectangle:
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
) -> IntersectionContext:
    """
    Construit toutes les informations réutilisables liées
    à la couche source.
    """

    return IntersectionContext(
        source_crs=source_layer.crs(),
        source_extent=source_layer.extent(),
    )


@dataclass(slots=True)
class TransformCache:
    _cache: dict[
        tuple[str, str],
        QgsCoordinateTransform,
    ] = field(default_factory=dict)

    def get(
        self,
        source_crs: QgsCoordinateReferenceSystem,
        target_crs: QgsCoordinateReferenceSystem,
    ) -> QgsCoordinateTransform:
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
    context: IntersectionContext,
    layer: QgsVectorLayer | QgsRasterLayer,
) -> bool:
    """
    Test rapide d'intersection d'emprises.
    """

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
    context: IntersectionContext,
    layers: list[QgsVectorLayer | QgsRasterLayer],
) -> list[QgsVectorLayer | QgsRasterLayer]:
    return [layer for layer in layers if may_intersect_source(context, layer)]

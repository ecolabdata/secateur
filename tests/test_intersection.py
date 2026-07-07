"""Tests for core.intersection (requires a real QGIS install via pytest-qgis)."""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsVectorLayer
from secateur.core.intersection.intersection_context import (
    TransformCache,
    build_intersection_context,
    filter_layers_by_extent,
    get_source_extent_in_crs,
    may_intersect_source,
)
from secateur.core.intersection.intersection_metrics import IntersectionMetrics
from secateur.core.intersection.intersection_processing import intersect_layers, prepare_layers

SOURCE_SQUARE_WKT = "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))"


def test_build_intersection_context(make_layer):
    source = make_layer("Polygon", "source", [(SOURCE_SQUARE_WKT, {"id": "1"})])

    context = build_intersection_context(source)

    assert context.source_crs == source.crs()
    assert context.source_extent == source.extent()
    assert context.include_raster is False
    assert context.metrics.layers == {}


def test_get_source_extent_in_crs_same_crs_returns_source_extent(make_layer):
    source = make_layer("Polygon", "source", [(SOURCE_SQUARE_WKT, {"id": "1"})])
    context = build_intersection_context(source)

    extent = get_source_extent_in_crs(context, source.crs())

    assert extent == context.source_extent


def test_may_intersect_source(make_layer):
    source = make_layer("Polygon", "source", [(SOURCE_SQUARE_WKT, {"id": "1"})])
    context = build_intersection_context(source)

    overlapping = make_layer("Point", "overlapping", [("POINT(5 5)", {"id": "1"})])
    far_away = make_layer("Point", "far", [("POINT(1000 1000)", {"id": "1"})])

    assert may_intersect_source(context, overlapping) is True
    assert may_intersect_source(context, far_away) is False


def test_filter_layers_by_extent(make_layer):
    source = make_layer("Polygon", "source", [(SOURCE_SQUARE_WKT, {"id": "1"})])
    context = build_intersection_context(source)

    overlapping = make_layer("Point", "overlapping", [("POINT(5 5)", {"id": "1"})])
    far_away = make_layer("Point", "far", [("POINT(1000 1000)", {"id": "1"})])

    assert filter_layers_by_extent(context, [overlapping, far_away]) == [overlapping]


def test_transform_cache_reuses_transform():
    cache = TransformCache()
    crs_a = QgsCoordinateReferenceSystem("EPSG:4326")
    crs_b = QgsCoordinateReferenceSystem("EPSG:2154")

    first = cache.get(crs_a, crs_b)
    second = cache.get(crs_a, crs_b)

    assert first is second


def test_intersection_metrics_get_layer_metrics_is_stable_per_layer():
    metrics = IntersectionMetrics()

    first = metrics.get_layer_metrics("layer_a")
    first.bbox_seconds = 1.5
    second = metrics.get_layer_metrics("layer_a")

    assert second is first
    assert second.bbox_seconds == 1.5


def test_prepare_and_intersect_layers(make_layer):
    # Same CRS on the project and the test layers so no reprojection is
    # exercised here (reprojection goes through QGIS Processing, which is
    # exercised separately by the extraction step below).
    QgsProject.instance().setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    source = make_layer("Polygon", "source", [(SOURCE_SQUARE_WKT, {"id": "src-1"})])
    candidate = make_layer(
        "Point",
        "candidate",
        [
            ("POINT(5 5)", {"name": "inside"}),
            ("POINT(1000 1000)", {"name": "outside"}),
        ],
    )

    context = build_intersection_context(source)
    prepared = prepare_layers([candidate], context)

    assert len(prepared) == 1

    results = intersect_layers(source, prepared, context)

    # The first result is always the source layer itself.
    assert len(results) == 2
    assert results[0].name() == source.name()

    intersected_layer = results[1]
    assert isinstance(intersected_layer, QgsVectorLayer)
    result_names = [feature["name"] for feature in intersected_layer.getFeatures()]
    assert result_names == ["inside"]

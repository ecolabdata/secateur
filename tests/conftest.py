"""Shared pytest fixtures for the secateur test suite.

These tests require pytest-qgis and a real QGIS >= 3.34 installation —
see the "Tests" section of the repository README for environment setup
(a venv created with ``uv venv --system-site-packages`` so it can see the
``qgis``/``qgis.PyQt`` modules bundled with QGIS).
"""

from collections.abc import Callable

import pytest
from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer


def _make_memory_layer(
    geometry_type: str,
    name: str,
    features: list[tuple[str, dict[str, str]]],
    crs: str = "EPSG:4326",
) -> QgsVectorLayer:
    """Build an in-memory vector layer populated with WKT geometries.

    Args:
        geometry_type: QGIS memory-provider geometry type, e.g. ``"Point"``
            or ``"Polygon"``.
        name: Layer name.
        features: List of ``(wkt, attributes)`` pairs. All attribute
            values are stored as strings for simplicity.
        crs: CRS assigned to the layer.

    Returns:
        A valid ``QgsVectorLayer`` with every feature in *features* added.
    """
    field_names = sorted({key for _, attrs in features for key in attrs})
    uri = f"{geometry_type}?crs={crs}"
    for field_name in field_names:
        uri += f"&field={field_name}:string"

    layer = QgsVectorLayer(uri, name, "memory")
    assert layer.isValid(), f"Failed to create memory layer with uri: {uri}"

    qgs_features = []
    for wkt, attrs in features:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromWkt(wkt))
        for key, value in attrs.items():
            feature.setAttribute(key, value)
        qgs_features.append(feature)

    layer.dataProvider().addFeatures(qgs_features)
    layer.updateExtents()

    return layer


@pytest.fixture
def make_layer() -> Callable[..., QgsVectorLayer]:
    """Return a factory for building small in-memory vector layers.

    Usage::

        def test_something(make_layer):
            layer = make_layer("Point", "source", [("POINT(0 0)", {"id": "1"})])
    """
    return _make_memory_layer


@pytest.fixture(scope="session", autouse=True)
def _initialize_processing(qgis_app):
    """Register QGIS Processing providers (native:*, gdal:*, ...).

    core.intersection.intersection_processing calls processing.run(...)
    directly; a standalone QgsApplication (as set up by pytest-qgis) does
    not register the Processing providers by itself.
    """
    from processing.core.Processing import Processing

    Processing.initialize()

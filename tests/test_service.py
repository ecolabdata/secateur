"""Tests for ui.service.SecateurService (requires a real QGIS via pytest-qgis).

SecateurService is deliberately Qt-free (see its docstring), so it can be
exercised directly against a fake `iface`-like object satisfying
QgisInterfaceProtocol, without any widget/event-loop involved.
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsMapLayer,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
)
from secateur.ui.service import SecateurService

SOURCE_SQUARE_WKT = "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))"


class FakeIface:
    """Minimal QgisInterfaceProtocol implementation for tests."""

    def __init__(self, active_layer: QgsMapLayer | None) -> None:
        self._active_layer = active_layer

    def activeLayer(self) -> QgsMapLayer | None:
        return self._active_layer


def test_select_no_active_layer_returns_warning():
    result = SecateurService().select(FakeIface(None))

    assert result.layer is None
    assert result.level == "warning"


def test_select_non_vector_layer_returns_warning():
    raster = QgsRasterLayer("", "not-a-vector")

    result = SecateurService().select(FakeIface(raster))

    assert result.layer is None
    assert result.level == "warning"


def test_select_no_feature_selected_returns_info(make_layer):
    layer = make_layer("Point", "source", [("POINT(1 1)", {"name": "a"})])

    result = SecateurService().select(FakeIface(layer))

    assert result.level == "info"
    assert result.layer is layer
    assert result.feature is None


def test_select_multiple_features_selected_returns_warning(make_layer):
    layer = make_layer(
        "Point",
        "source",
        [("POINT(1 1)", {"name": "a"}), ("POINT(2 2)", {"name": "b"})],
    )
    layer.select([feature.id() for feature in layer.getFeatures()])

    result = SecateurService().select(FakeIface(layer))

    assert result.level == "warning"
    assert result.layer is layer


def test_select_single_feature_materializes_memory_layer(make_layer):
    layer = make_layer("Point", "source", [("POINT(1 1)", {"name": "a"})])
    QgsProject.instance().addMapLayer(layer)
    layer.select([next(layer.getFeatures()).id()])

    result = SecateurService().select(FakeIface(layer))

    assert result.level == "info"
    assert result.feature is not None
    assert result.layer is not None
    assert result.layer.name().startswith("source_feature_")


def test_run_with_unknown_layer_id_returns_error():
    result = SecateurService().run("not-a-real-layer-id", QgsProcessingFeedback())

    assert result.level == "error"
    assert result.result_layer_ids == []


def test_run_produces_intersection_results(make_layer):
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    source = make_layer("Polygon", "source", [(SOURCE_SQUARE_WKT, {"id": "src"})])
    candidate = make_layer("Point", "candidate", [("POINT(5 5)", {"name": "inside"})])
    project.addMapLayers([source, candidate])

    result = SecateurService().run(source.id(), QgsProcessingFeedback())

    assert result.level == "info"
    # The source layer itself plus one intersected candidate layer.
    assert len(result.result_layer_ids) == 2

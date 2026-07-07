"""Tests for core.utils (requires a real QGIS install via pytest-qgis)."""

import re

from qgis.core import QgsProject, QgsRasterLayer
from qgis.PyQt.QtCore import QDate
from secateur.core.constants import BASEMAP_GROUP_NAME, CREATED_OBJECTS_GROUP_NAME, RESULT_GROUP_NAME
from secateur.core.utils.formatting import _format_value, _safe_filename, display_date_str, timestamp_str
from secateur.core.utils.layer_resolver import LayerResolver
from secateur.core.utils.layers import (
    find_group,
    find_layers,
    find_tree_layer,
    get_basemap_group,
    get_created_objects_group,
    get_or_create_group,
    get_results_group,
    iter_visible_layers,
    iterate_layers,
)

# ──────────────────────────────────────────────
#  LayerResolver
# ──────────────────────────────────────────────


def test_layer_resolver_get_returns_none_for_empty_id():
    assert LayerResolver.get("") is None


def test_layer_resolver_get_returns_layer_by_id(make_layer):
    layer = make_layer("Point", "l", [("POINT(0 0)", {})])
    QgsProject.instance().addMapLayer(layer)

    assert LayerResolver.get(layer.id()) is layer


def test_layer_resolver_get_vector_rejects_raster():
    raster = QgsRasterLayer("", "not-a-vector")
    QgsProject.instance().addMapLayer(raster)

    assert LayerResolver.get_vector(raster.id()) is None


def test_layer_resolver_get_many_skips_unknown_ids(make_layer):
    layer_a = make_layer("Point", "a", [("POINT(0 0)", {})])
    layer_b = make_layer("Point", "b", [("POINT(1 1)", {})])
    QgsProject.instance().addMapLayers([layer_a, layer_b])

    result = LayerResolver.get_many([layer_a.id(), "not-a-real-id", layer_b.id()])

    assert result == [layer_a, layer_b]


# ──────────────────────────────────────────────
#  Layer-tree groups
# ──────────────────────────────────────────────


def test_get_or_create_group_creates_and_is_findable():
    group = get_or_create_group(["TestGroup"])

    assert group is not None
    assert group.name() == "TestGroup"
    assert find_group(["TestGroup"]) is not None


def test_get_or_create_group_nested_path():
    group = get_or_create_group(["Parent", "Child"])

    assert group is not None
    assert group.name() == "Child"
    assert find_group(["Parent"]) is not None
    assert find_group(["Parent", "Child"]) is not None


def test_get_or_create_group_clear_removes_children(make_layer):
    group = get_or_create_group(["ClearMe"])
    assert group is not None
    layer = make_layer("Point", "l", [("POINT(0 0)", {})])
    QgsProject.instance().addMapLayer(layer, False)
    group.addLayer(layer)
    assert len(group.children()) == 1

    cleared = get_or_create_group(["ClearMe"], clear=True)

    assert cleared is not None
    assert len(cleared.children()) == 0


def test_named_groups_use_expected_constants():
    results_group = get_results_group()
    created_objects_group = get_created_objects_group()
    basemap_group = get_basemap_group()

    assert results_group is not None
    assert created_objects_group is not None
    assert basemap_group is not None
    assert results_group.name() == RESULT_GROUP_NAME
    assert created_objects_group.name() == CREATED_OBJECTS_GROUP_NAME
    assert basemap_group.name() == BASEMAP_GROUP_NAME


def test_find_tree_layer(make_layer):
    root = QgsProject.instance().layerTreeRoot()
    layer = make_layer("Point", "l", [("POINT(0 0)", {})])
    QgsProject.instance().addMapLayer(layer)
    other = make_layer("Point", "other", [("POINT(0 0)", {})])

    assert find_tree_layer(root, layer) is not None
    assert find_tree_layer(root, other) is None


def test_iter_visible_layers_skips_hidden(make_layer):
    root = QgsProject.instance().layerTreeRoot()
    visible = make_layer("Point", "visible", [("POINT(0 0)", {})])
    hidden = make_layer("Point", "hidden", [("POINT(0 0)", {})])
    QgsProject.instance().addMapLayers([visible, hidden])
    root.findLayer(hidden.id()).setItemVisibilityChecked(False)

    result = list(iter_visible_layers(root))

    assert visible in result
    assert hidden not in result


def test_find_layers_excludes_given_layer(make_layer):
    layer_a = make_layer("Point", "a", [("POINT(0 0)", {})])
    layer_b = make_layer("Point", "b", [("POINT(0 0)", {})])
    QgsProject.instance().addMapLayers([layer_a, layer_b])

    result = find_layers(exclude=layer_a)

    assert layer_a not in result
    assert layer_b in result


def test_iterate_layers_calls_callback_for_each_item(make_layer):
    layers = [
        make_layer("Point", "a", [("POINT(0 0)", {})]),
        make_layer("Point", "b", [("POINT(1 1)", {})]),
        make_layer("Point", "c", [("POINT(2 2)", {})]),
    ]
    seen = []

    iterate_layers(layers, seen.append)

    assert seen == layers


# ──────────────────────────────────────────────
#  Formatting
# ──────────────────────────────────────────────


def test_timestamp_str_format():
    assert re.match(r"^\d{4}_\d{2}_\d{2}_\d{2}h_\d{2}min$", timestamp_str())


def test_display_date_str_format():
    assert re.match(r"^\d{2}/\d{2}/\d{4}$", display_date_str())


def test_format_value_none_returns_empty_string():
    assert _format_value(None) == ""


def test_format_value_passthrough_for_plain_types():
    assert _format_value(42) == 42
    assert _format_value("hello") == "hello"


def test_format_value_formats_qdate():
    assert _format_value(QDate(2026, 7, 7)) == "2026-07-07"


def test_safe_filename_replaces_unsafe_characters():
    assert _safe_filename("layer/name:*?") == "layer_name___"

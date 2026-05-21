"""Visibility helpers extracted from...utils.
Exports:
- clear_all_visibility (context manager to hide all layers)
- set_layer_and_parents_visible (make a layer visible recursively)
"""

from contextlib import contextmanager

from qgis.core import QgsLayerTreeGroup, QgsMapLayer

from ..logger import logger
from .rendering import is_simple_fill, set_layer_opacity


def set_layer_and_parents_visible(root: QgsLayerTreeGroup, layer: QgsMapLayer) -> bool:
    """Make *layer* and all its parent groups visible.

    Returns ``True`` if the layer was found and visibility changed, ``False`` otherwise.
    """
    tree_layer = root.findLayer(layer.id())
    if not tree_layer:
        return False
    tree_layer.setItemVisibilityCheckedParentRecursive(True)
    tree_layer.setItemVisibilityChecked(True)
    return True


@contextmanager
def clear_all_visibility(root):
    """Hide all layers for the duration of the context.

    Visibility changes performed inside the context are kept; original state is not restored.
    """
    for node in root.findLayers():
        node.setItemVisibilityChecked(False)
    try:
        yield
    finally:
        pass


@contextmanager
def temporary_visible_layers(root, result_layers: list[QgsMapLayer], basemap_layer: QgsMapLayer | None):
    """Temporarily hide all layers then make *result_layers* (and optional *basemap_layer*) visible.

    Yields the list of layer names used for the legend.
    """
    visible_count = 0
    # Hide everything via the existing ``clear_all_visibility`` helper
    with clear_all_visibility(root):

        def _make_visible(layer):
            nonlocal visible_count
            try:
                if is_simple_fill(layer):
                    set_layer_opacity(layer, opacity=0.8)
                visible_count += int(set_layer_and_parents_visible(root, layer))
            except Exception as exc:
                logger.exception("Could not set visibility for layer %s: %s", layer.name(), exc)

        for layer in result_layers:
            _make_visible(layer)
        if visible_count == 0:
            logger.warning("temporary_visible_layers: no result layers could be made visible")
        if basemap_layer is not None:
            try:
                visible_count += int(set_layer_and_parents_visible(root, basemap_layer))
            except Exception as exc:
                logger.exception("Could not set visibility for basemap layer %s: %s", basemap_layer.name(), exc)
        layer_names = [lyr.name() for lyr in result_layers]
        yield layer_names

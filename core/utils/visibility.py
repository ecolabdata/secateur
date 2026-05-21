"""Visibility helpers extracted from core.utils.
Exports:
- clear_all_visibility (context manager to hide all layers)
- set_layer_and_parents_visible (make a layer visible recursively)
"""

from contextlib import contextmanager
from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer, QgsMapLayer


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

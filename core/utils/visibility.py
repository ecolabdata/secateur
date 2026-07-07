"""Visibility helpers extracted from...utils.
Exports:
- clear_all_visibility (context manager to hide all layers)
- set_layer_and_parents_visible (make a layer visible recursively)
"""

from contextlib import contextmanager

from qgis.core import QgsLayerTreeGroup, QgsMapLayer

from .layers import find_tree_layer


def set_layer_visible(
    root: QgsLayerTreeGroup,
    layer: QgsMapLayer,
    visible: bool,
) -> bool:
    """Set *layer*'s visibility checkbox under *root*.

    Args:
        root: Layer tree group to search under.
        layer: Layer whose visibility is changed.
        visible: Whether the layer should be checked visible.

    Returns:
        ``True`` if the layer was found and updated, ``False`` otherwise.
    """
    if tree_layer := find_tree_layer(root, layer):
        tree_layer.setItemVisibilityChecked(visible)
        return True
    return False


def set_layer_and_parents_visible(root: QgsLayerTreeGroup, layer: QgsMapLayer) -> bool:
    """Make *layer* and all its parent groups visible.

    Returns ``True`` if the layer was found and visibility changed, ``False`` otherwise.
    """
    if tree_layer := find_tree_layer(root, layer):
        tree_layer.setItemVisibilityCheckedParentRecursive(True)
        tree_layer.setItemVisibilityChecked(True)
        return True
    return False


@contextmanager
def clear_all_visibility(root: QgsLayerTreeGroup):
    """Hide all layers for the duration of the context.

    Visibility changes performed inside the context are kept; original state is not restored.
    """
    for node in root.findLayers():
        node.setItemVisibilityChecked(False)
    try:
        yield
    finally:
        pass

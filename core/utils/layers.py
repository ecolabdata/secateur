"""Layer‑tree utilities extracted from...utils.
Exports functions for group handling, layer discovery and iteration.
"""

from qgis.core import (
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsProject,
    QgsVectorLayer,
)

from ..constants import CREATED_OBJECTS_GROUP_NAME, RESULT_GROUP_NAME
from ..logger import logger


def get_or_create_group(path: list[str], clear: bool = False):
    """Return or create a :class:`QgsLayerTreeGroup`.

    *path* – list of group names representing the hierarchy.
    If the group does not exist, it is created (including any missing parent
    groups). When *clear* is ``True``, all children of the group are removed.
    """
    project = QgsProject.instance()
    if not project:
        return None

    node = project.layerTreeRoot()
    for name in path:
        if not node:
            return None
        node = next(
            (child for child in node.children() if isinstance(child, QgsLayerTreeGroup) and child.name() == name),
            None,
        )
        if node is None:
            break
    group = node

    if group is None:
        root = project.layerTreeRoot()
        if len(path) > 1:
            parent_path = path[:-1]
            parent_group = get_or_create_group(parent_path, clear=False)
            if parent_group is None:
                parent_group = root
            group = parent_group.insertGroup(0, path[-1])
        else:
            group = root.insertGroup(0, path[0])

    if clear and group is not None:
        group.removeAllChildren()

    return group


def get_results_group(clear: bool = False):
    """Return the "Résultats secateur" group, creating it if necessary.
    Pass ``clear=True`` to empty the group before returning.
    """
    return get_or_create_group([RESULT_GROUP_NAME], clear=clear)


def get_created_objects_group(clear: bool = False):
    """Return the "Objets créés" group, creating it if necessary.
    Pass ``clear=True`` to empty the group before returning.
    """
    return get_or_create_group([CREATED_OBJECTS_GROUP_NAME], clear=clear)


def filter_out_source(layers: list[QgsVectorLayer], source: QgsVectorLayer) -> list[QgsVectorLayer]:
    """Return a new list of *layers* without the *source* layer."""
    return [lyr for lyr in layers if lyr != source]


def find_layers(exclude: QgsVectorLayer | None = None) -> list[QgsVectorLayer]:
    """Return a list of visible vector layers in the current QGIS project.

    Args:
        exclude: Optional ``QgsVectorLayer`` that will be omitted from the result.
    """
    project = QgsProject.instance()
    if project is None:
        return []
    root = project.layerTreeRoot()
    if root is None:
        return []
    results: list[QgsVectorLayer] = []
    _collect_layers(root, results, exclude)
    return results


def _collect_layers(group: QgsLayerTreeGroup, out: list[QgsVectorLayer], exclude):
    """Recursively collect visible vector layers from *group* into *out*."""
    for child in group.children():
        if isinstance(child, QgsLayerTreeGroup):
            if child.isVisible():
                _collect_layers(child, out, exclude)
        elif isinstance(child, QgsLayerTreeLayer):
            if not child.isVisible():
                continue
            layer = child.layer()
            if isinstance(layer, QgsVectorLayer) and layer != exclude:
                out.append(layer)


def iterate_layers(layers, callback, feedback=None):
    """Iterate over *layers* and apply *callback* to each.

    ``feedback`` – optional :class:`QgsProcessingFeedback` instance.  If provided,
    its ``setProgress`` method is called with ``int(i / total * 100)`` before
    invoking the callback.  If the user cancels the associated task, the loop
    aborts early.
    """
    total = len(layers)
    for i, layer in enumerate(layers):
        if feedback:
            feedback.setProgress(int(i / total * 100))
            if getattr(feedback, "isCanceled", lambda: False)():
                logger.info("Export cancelled by user after %d/%d layers", i, total)
                break
        callback(layer)

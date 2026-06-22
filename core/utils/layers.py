"""Layer‑tree utilities extracted from...utils.
Exports functions for group handling, layer discovery and iteration.
"""

from collections.abc import Callable, Iterator, Sequence
from typing import TypeVar

from qgis.core import (
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsMapLayer,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

from ..constants import BASEMAP_GROUP_NAME, CREATED_OBJECTS_GROUP_NAME, RESULT_GROUP_NAME
from ..logger import logger

# Generic type for layer iteration (covariant)
T = TypeVar("T", bound=QgsMapLayer, covariant=True)


def _walk_group_path(
    root: QgsLayerTreeGroup,
    path: Sequence[str],
) -> QgsLayerTreeGroup | None:
    node: QgsLayerTreeGroup | None = root

    for name in path:
        node = next(
            (child for child in node.children() if isinstance(child, QgsLayerTreeGroup) and child.name() == name),
            None,
        )

        if node is None:
            return None

    return node


def find_group(path: list[str]) -> QgsLayerTreeGroup | None:
    """Return the group identified by *path* or None if it does not exist."""
    project = QgsProject.instance()
    if not project:
        return None

    return _walk_group_path(project.layerTreeRoot(), path)


def get_or_create_group(path: list[str], clear: bool = False, insert: int = 0) -> QgsLayerTreeGroup | None:
    """Return or create a :class:`QgsLayerTreeGroup`.

    *path* – list of group names representing the hierarchy.
    If the group does not exist, it is created (including any missing parent
    groups). When *clear* is ``True``, all children of the group are removed.
    When *insert* is `0` add at the top of the layer tree, `-1` is bottom.
    """
    project = QgsProject.instance()
    if not project:
        return None

    group = _walk_group_path(project.layerTreeRoot(), path)
    if group is None:
        root = project.layerTreeRoot()
        if len(path) > 1:
            parent_path = path[:-1]
            parent_group = get_or_create_group(parent_path, clear=False)
            if parent_group is None:
                parent_group = root
            group = parent_group.insertGroup(insert, path[-1])
        else:
            group = root.insertGroup(insert, path[0])

    if clear and group is not None:
        group.removeAllChildren()

    return group


def get_results_group(clear: bool = False) -> QgsLayerTreeGroup | None:
    """Return the "Résultats secateur" group, creating it if necessary.
    Pass ``clear=True`` to empty the group before returning.
    """
    return get_or_create_group([RESULT_GROUP_NAME], clear=clear)


def get_created_objects_group(clear: bool = False) -> QgsLayerTreeGroup | None:
    """Return the "Objets créés" group, creating it if necessary.
    Pass ``clear=True`` to empty the group before returning.
    """
    return get_or_create_group([CREATED_OBJECTS_GROUP_NAME], clear=clear)


def get_basemap_group(clear: bool = False) -> QgsLayerTreeGroup | None:
    """Return the "Fonds de carte" group, creating it at bottom if necessary.
    Pass ``clear=True`` to empty the group before returning.
    """
    return get_or_create_group([BASEMAP_GROUP_NAME], clear=clear, insert=-1)


def filter_out_source(layers: list[QgsVectorLayer], source: QgsVectorLayer) -> list[QgsVectorLayer]:
    """Return a new list of *layers* without the *source* layer."""
    return [lyr for lyr in layers if lyr != source]


def find_tree_layer(
    root: QgsLayerTreeGroup,
    layer: QgsMapLayer,
):
    return root.findLayer(layer.id())


def iter_visible_layers(
    group: QgsLayerTreeGroup,
    exclude: QgsMapLayer | None = None,
    include_raster: bool = False,
) -> Iterator[QgsMapLayer]:
    for child in group.children():
        if isinstance(child, QgsLayerTreeGroup):
            if child.isVisible():
                yield from iter_visible_layers(child, exclude, include_raster=include_raster)

        elif isinstance(child, QgsLayerTreeLayer):
            if not child.isVisible():
                continue

            layer = child.layer()
            if not include_raster and isinstance(layer, QgsRasterLayer):
                continue
            if layer != exclude:
                yield layer


def _root() -> QgsLayerTreeGroup | None:
    project = QgsProject.instance()
    return project.layerTreeRoot() if project else None


def find_layers(exclude: QgsMapLayer | None = None, include_raster: bool = False) -> list[QgsMapLayer]:
    """Return a list of visible vector layers in the current QGIS project.

    Args:
        exclude: Optional ``QgsVectorLayer`` that will be omitted from the result.
    """
    root = _root()
    if root is None:
        return []

    return list(
        iter_visible_layers(
            root,
            exclude,
            include_raster=include_raster,
        )
    )


def iterate_layers(
    layers: Sequence[T],
    callback: Callable[[T], None],
    feedback: QgsProcessingFeedback | None = None,
) -> None:
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

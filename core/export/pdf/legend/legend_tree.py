"""Utility functions for building and configuring QGIS legend trees safely.

The functions ensure that ownership of the created ``QgsLayerTree`` is transferred
to the ``QgsLayoutItemLegend`` without retaining any Python references that could
lead to dangling SIP objects.
"""

import textwrap

from qgis.core import QgsLayerTree, QgsLayoutItemLegend, QgsPrintLayout, QgsProject


def build_legend_tree(*, project: QgsProject, layer_names: list[str]) -> QgsLayerTree:
    """Create a ``QgsLayerTree`` populated with the given layer names.

    The function creates a new ``QgsLayerTree`` instance, adds each layer found
    in *project* matching *layer_names*, and wraps long layer names to avoid
    overflow in the legend display.
    """
    root = QgsLayerTree()
    root.setName("LegendRoot")

    # Build lookup table once to avoid O(n*m) lookups
    layers_by_name = {layer.name(): layer for layer in project.mapLayers().values()}

    for layer_name in layer_names:
        layer = layers_by_name.get(layer_name)
        if not layer:
            continue
        node = root.addLayer(layer)
        # Wrap long names for better layout rendering
        wrapped_name = "\n".join(textwrap.wrap(node.name(), width=100))
        node.setName(wrapped_name)
    return root


def configure_legend(
    *,
    legend: QgsLayoutItemLegend,
    layout: QgsPrintLayout,
    project: QgsProject,
    layer_names: list[str],
) -> None:
    """Configure *legend* with a fresh layer tree built from *layer_names*.

    The function disables automatic model updates, sets the newly built tree as the
    root group, and performs the recommended refresh sequence for QGIS 3.34.
    """
    legend.setAutoUpdateModel(False)

    legend_root = build_legend_tree(
        project=project,
        layer_names=layer_names,
    )

    legend.model().setRootGroup(legend_root)

    # Keep strong Python ownership alive for the whole layout lifecycle.
    layout._secateur_legend_root = legend_root

    legend.invalidateCache()
    legend.updateLegend()
    legend.refresh()
    legend.adjustBoxSize()

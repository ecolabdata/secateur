"""Utility functions for building and configuring QGIS legend trees safely.

The functions ensure that ownership of the created ``QgsLayerTree`` is transferred
to the ``QgsLayoutItemLegend`` without retaining any Python references that could
lead to dangling SIP objects.
"""

import textwrap

from qgis.core import QgsLayerTree, QgsLayoutItemLegend, QgsProject


def build_legend_tree(*, project: QgsProject, layer_names: list[str]) -> QgsLayerTree:
    """Create a ``QgsLayerTree`` populated with the given layer names.

    The function creates a new ``QgsLayerTree`` instance, adds each layer found
    in *project* matching *layer_names*, and wraps long layer names to avoid
    overflow in the legend display.
    """
    root = QgsLayerTree()
    root.setName("LegendRoot")

    for layer_name in layer_names:
        layers = project.mapLayersByName(layer_name)
        if not layers:
            continue
        layer = layers[0]
        node = root.addLayer(layer)
        # Wrap long names for better layout rendering
        wrapped_name = "\n".join(textwrap.wrap(node.name(), width=100))
        node.setName(wrapped_name)
    return root


def configure_legend(*, legend: QgsLayoutItemLegend, project: QgsProject, layer_names: list[str]) -> None:
    """Configure *legend* with a fresh layer tree built from *layer_names*.

    The function disables automatic model updates, sets the newly built tree as the
    root group, and performs the recommended refresh sequence for QGIS 3.34.
    No Python reference to the tree is retained after the call.
    """
    legend.setAutoUpdateModel(False)
    root = build_legend_tree(project=project, layer_names=layer_names)
    legend.model().setRootGroup(root)
    # Recommended refresh order for QGIS 3.34
    legend.invalidateCache()
    legend.updateLegend()
    legend.refresh()
    legend.adjustBoxSize()

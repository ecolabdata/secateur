"""
Visibility management utilities for GeoPDF export.

This module provides helper functions for managing layer visibility
during GeoPDF exports.
"""

from contextlib import contextmanager

from qgis.core import QgsMapLayer, QgsProcessingFeedback

from ...logger import logger
from ...utils.rendering import is_simple_fill, set_layer_opacity
from ...utils.visibility import clear_all_visibility, set_layer_and_parents_visible


@contextmanager
def temporary_visible_layers(
    root,
    result_layers: list[QgsMapLayer],
    basemap_layer: QgsMapLayer | None,
    feedback: QgsProcessingFeedback | None = None,
):
    """Temporarily hide all layers then make *result_layers* (and optional *basemap_layer*) visible.

    Yields the list of layer names used for the legend.
    """
    visible_count = 0
    # Hide everything via the existing ``clear_all_visibility`` helper
    with clear_all_visibility(root):
        # Update feedback after making layers visible
        from ...utils.feedback import update_feedback

        update_feedback(feedback, 20, "Couches de résultat rendues visibles")

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

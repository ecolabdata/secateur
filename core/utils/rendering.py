"""Rendering‑related helpers extracted from...utils.
Exports:
- set_layer_opacity
- is_simple_fill
"""

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsRenderContext,
    QgsSingleSymbolRenderer,
)


def set_layer_opacity(layer, opacity):
    """Set the opacity of a layer's renderer symbols.

    Supports ``QgsSingleSymbolRenderer`` and ``QgsCategorizedSymbolRenderer``.
    If the layer has no renderer, the function does nothing.
    """
    renderer = layer.renderer()
    if renderer is None:
        return
    context = QgsRenderContext()
    if isinstance(renderer, QgsSingleSymbolRenderer):
        symbol = renderer.symbol()
        symbol.setOpacity(opacity)
    elif isinstance(renderer, QgsCategorizedSymbolRenderer):
        for symbol in renderer.symbols(context):
            symbol.setOpacity(opacity)


def is_simple_fill(layer):
    """Determine if a layer's renderer uses only simple fill symbols.

    Returns ``True`` when the renderer is a ``QgsSingleSymbolRenderer`` with a
    ``QgsFillSymbol`` or a ``QgsCategorizedSymbolRenderer`` whose all category
    symbols are ``QgsFillSymbol`` instances. Otherwise returns ``False``.
    """
    renderer = layer.renderer()
    if renderer is None:
        return False
    if isinstance(renderer, QgsSingleSymbolRenderer):
        return isinstance(renderer.symbol(), QgsFillSymbol)
    if isinstance(renderer, QgsCategorizedSymbolRenderer):
        context = QgsRenderContext()
        return all(isinstance(s, QgsFillSymbol) for s in renderer.symbols(context))
    return False

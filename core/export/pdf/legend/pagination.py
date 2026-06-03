"""Pagination utilities for legend export.

This module provides thin wrappers around the historic ``LegendItemCounter``
and ``LegendPaginationService`` implementation. Keeping them in a dedicated
module satisfies the new architecture requirement without duplicating logic.
"""

from dataclasses import dataclass

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsGraduatedSymbolRenderer,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)

from ....logger import logger


@dataclass(slots=True)
class LegendPage:
    """Domain entity representing a legend page."""

    layer_names: list[str]
    estimated_cost: int


class LegendItemCounter:
    """Calculate the logical cost of a layer for legend pagination."""

    def count(self, layer: QgsVectorLayer) -> int:
        """
        Calculate the cost of a layer in terms of legend items.

        Cost is calculated based on:
        - Title (always 1)
        - Symbols (1 each)
        - Categories (1 each)
        - Ranges (1 each)
        - Rules (1 each)
        """
        renderer = layer.renderer()
        if renderer is None:
            logger.warning(f"Layer '{layer.name()}' has no renderer, using fallback cost of 5")
            return 5

        # Determine renderer type and calculate cost
        if isinstance(renderer, QgsSingleSymbolRenderer):
            # 1 title + 1 symbol = 2
            return 2

        elif isinstance(renderer, QgsCategorizedSymbolRenderer):
            # 1 title + number of categories
            categories = renderer.categories()
            return 1 + len(categories)

        elif isinstance(renderer, QgsGraduatedSymbolRenderer):
            # 1 title + number of ranges
            ranges = renderer.ranges()
            return 1 + len(ranges)

        elif isinstance(renderer, QgsRuleBasedRenderer):
            # 1 title + number of visible rules (recursive)
            return 1 + self._count_rules(renderer.rootRule())

        else:
            # Fallback for unknown renderers
            logger.warning(
                f"Unknown renderer type for layer '{layer.name()}': {type(renderer).__name__}, using fallback cost of 5"
            )
            return 5

    def _count_rules(self, rule) -> int:
        """
        Recursively count active legend rules.

        Only counts rules that are active and have symbols.
        """
        if not rule:
            return 0

        count = 0

        # Count only active rules with symbols
        if rule.isActive() and rule.symbol() is not None:
            count += 1

        # Recursively count child rules
        for child_rule in rule.children():
            count += self._count_rules(child_rule)

        return count


class LegendPaginationService:
    """
    Paginate layers based on their estimated legend item cost.
    """

    def __init__(
        self,
        project: QgsProject,
        counter: LegendItemCounter,
        max_items_per_page: int,
    ):
        self.project = project
        self.counter = counter
        self.max_items_per_page = max_items_per_page

    def paginate(self, layer_names: list[str]) -> list[LegendPage]:
        """
        Paginate layers according to their legend complexity.

        Returns a list of ``LegendPage`` objects, each containing the
        layer names for that page and the total estimated cost.

        Strategy:
        - accumulate layers until max_items_per_page is reached
        - if a single layer exceeds the limit, place it alone
        """
        if not layer_names:
            raise ValueError("No layers provided for export")

        # Build lookup table once to avoid O(n*m) lookups
        layers_by_name = {layer.name(): layer for layer in self.project.mapLayers().values()}

        pages: list[LegendPage] = []

        current_page: list[str] = []
        current_cost = 0

        for layer_name in layer_names:
            layer = layers_by_name.get(layer_name)

            if not layer:
                logger.warning(f"Layer '{layer_name}' not found in project")
                continue

            # Fallback cost for non-vector layers
            if not isinstance(layer, QgsVectorLayer):
                logger.warning(f"Layer '{layer_name}' is not a vector layer, using fallback cost of 5")
                layer_cost = 5
            else:
                layer_cost = self.counter.count(layer)

            logger.debug(f"Layer '{layer_name}' legend cost = {layer_cost}")

            if current_page and (current_cost + layer_cost > self.max_items_per_page):
                pages.append(LegendPage(current_page, current_cost))
                current_page = []
                current_cost = 0

            current_page.append(layer_name)
            current_cost += layer_cost

        # Final page
        if current_page:
            pages.append(LegendPage(current_page, current_cost))

        logger.info(f"Legend pagination complete: {len(pages)} page(s) generated")

        return pages

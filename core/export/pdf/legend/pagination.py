"""Pagination utilities for legend export.

This module provides thin wrappers around the historic ``LegendItemCounter``
and ``LegendPaginationService`` implementation. Keeping them in a dedicated
module satisfies the new architecture requirement without duplicating logic.
"""

# Re-export legacy implementations for ease of import
from ....legend_exporter import LegendItemCounter, LegendPaginationService

__all__ = ["LegendItemCounter", "LegendPaginationService"]

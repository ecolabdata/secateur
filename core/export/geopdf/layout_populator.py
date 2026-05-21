"""
Layout populator utilities for GeoPDF export.
"""

import os

from qgis.core import QgsLayoutItemLabel, QgsLayoutItemPicture, QgsPrintLayout

from .layout_items import resolve_layout_items


def populate_layout_texts(
    layout: QgsPrintLayout,
    title: str,
    author: str,
    date_hm: str,
) -> None:
    """Populate text items in the layout with dynamic content.

    Updates the 'title', 'author', and 'date' label items.
    """
    items = resolve_layout_items(layout)
    # Title
    title_item = items.title_item
    if not isinstance(title_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'title' is not a QgsLayoutItemLabel, got {type(title_item)}")
    title_item.setText(title)
    title_item.refresh()

    # Author
    author_item = items.author_item
    if not isinstance(author_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'author' is not a QgsLayoutItemLabel, got {type(author_item)}")
    author_item.setText(author or "")
    author_item.refresh()

    # Date
    date_item = items.date_item
    if not isinstance(date_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'date' is not a QgsLayoutItemLabel, got {type(date_item)}")
    date_item.setText(date_hm)
    date_item.refresh()


def populate_layout_logo(
    layout: QgsPrintLayout,
    logo_path: str | None,
) -> None:
    """Populate the logo picture item in the layout with a dynamic logo.

    If ``logo_path`` is provided and points to an existing file, the picture
    path is set; otherwise the logo item is left unchanged.
    """
    items = resolve_layout_items(layout)
    logo_item = items.logo_item

    if not isinstance(logo_item, QgsLayoutItemPicture):
        raise TypeError(f"Layout item 'logo' is not a QgsLayoutItemPicture, got {type(logo_item)}")

    if logo_path and os.path.exists(logo_path):
        logo_item.setPicturePath(logo_path)
        logo_item.refresh()

"""
Layout‑level metadata utilities.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from qgis.core import QgsLayout, QgsLayoutItemLabel, QgsLayoutItemPicture

from ..models import LayoutMetadata

if TYPE_CHECKING:
    from .metadata_items import MetadataLayoutItems


def apply_label_text(item: QgsLayoutItemLabel | None, text: str) -> None:
    """Apply text to a label item."""
    if item is not None:
        item.setText(text)
        item.refresh()


def apply_logo(item: QgsLayoutItemPicture | None, logo_path: Path | None) -> None:
    """Apply logo to a picture item."""
    if item is not None and logo_path and logo_path.exists():
        item.setPicturePath(str(logo_path))
        item.refresh()


def inject_basic_metadata(
    *,
    title_item,
    author_item,
    date_item,
    logo_item,
    metadata: LayoutMetadata,
) -> None:
    """Inject basic metadata into layout items."""
    apply_label_text(title_item, metadata.title)
    apply_label_text(author_item, f"Auteur: {metadata.author}")
    apply_label_text(date_item, metadata.date_text)
    apply_logo(logo_item, metadata.logo_path)


class MetadataRenderer:
    """Centralized metadata renderer for PDF layouts."""

    @staticmethod
    def render(
        layout: QgsLayout,
        metadata: LayoutMetadata,
        metadata_items: "MetadataLayoutItems",
    ) -> None:
        """
        Render metadata into the given layout using the provided metadata items.

        Args:
            layout: The QGIS layout to populate with metadata
            metadata: The metadata to render
            metadata_items: The metadata layout items to populate
        """
        inject_basic_metadata(
            title_item=metadata_items.title_item,
            author_item=metadata_items.author_item,
            date_item=metadata_items.date_item,
            logo_item=metadata_items.logo_item,
            metadata=metadata,
        )

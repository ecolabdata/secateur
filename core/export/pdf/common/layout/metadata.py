"""
Layout‑level metadata utilities.
"""

from pathlib import Path

from ..models import LayoutMetadata


def apply_label_text(item, text: str) -> None:
    """Apply text to a label item."""
    if item is not None:
        item.setText(text)
        item.refresh()


def apply_logo(item, logo_path: Path | None) -> None:
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
    metadata: "LayoutMetadata",
) -> None:
    """Inject basic metadata into layout items."""
    apply_label_text(title_item, metadata.title)
    apply_label_text(author_item, f"Auteur: {metadata.author}")
    apply_label_text(date_item, metadata.date_text)
    apply_logo(logo_item, metadata.logo_path)

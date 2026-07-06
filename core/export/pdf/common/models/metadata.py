from dataclasses import dataclass
from pathlib import Path

from .....utils.formatting import display_date_str


@dataclass(slots=True)
class LayoutMetadata:
    """Metadata values (title, author, date, logo) applied to a PDF layout."""

    title: str
    author: str
    date_text: str
    logo_path: Path | None = None


@dataclass(slots=True)
class LayoutMetadataFactory:
    """Factory for creating LayoutMetadata instances."""

    @staticmethod
    def create(
        title: str,
        author: str,
        logo_path: Path | None = None,
    ) -> LayoutMetadata:
        """Create a LayoutMetadata instance with the current date."""
        return LayoutMetadata(
            title=title,
            author=author,
            date_text=display_date_str(),
            logo_path=logo_path,
        )

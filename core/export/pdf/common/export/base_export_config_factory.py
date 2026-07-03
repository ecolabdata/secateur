"""
Base configuration factory for PDF export.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..path_resolver import resolve_output_path, resolve_resource_base_path


@dataclass
class ExportConfig:
    """Simple base configuration object returned by factories."""

    output_path: Path
    template_path: Path
    title: str
    author: str
    logo_path: Path | None = None


@dataclass
class ExportConfigFactory(ABC):
    """Factory for creating ExportConfig instances."""

    @classmethod
    @abstractmethod
    def _get_template_filename(cls) -> str:
        """Get the template filename for this configuration type."""
        ...

    @classmethod
    @abstractmethod
    def _get_default_output_filename(cls, timestamp: str) -> str:
        """Get the default output filename for this configuration type."""
        ...

    @classmethod
    def default(
        cls: type["ExportConfigFactory"],
        *,
        output_path: str | Path,
        title: str,
        author: str,
        logo_path: str | Path | None = None,
    ) -> "ExportConfig":
        """Create a default configuration with common setup.

        Resolves the output path (adds timestamped filename if a directory is given),
        sets the template path to the bundled layout, and normalises the logo path.
        """
        resource_base = resolve_resource_base_path(__file__)
        output_path_obj, template_path = resolve_output_path(
            output_path,
            cls._get_default_output_filename("{timestamp}"),
            cls._get_template_filename(),
            resource_base,
        )
        return ExportConfig(
            output_path=output_path_obj,
            template_path=template_path,
            title=title,
            author=author,
            logo_path=Path(logo_path) if logo_path else None,
        )

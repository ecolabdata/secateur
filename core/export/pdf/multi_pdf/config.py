"""
Configuration objects for Multi-Page PDF export.
"""

from dataclasses import dataclass
from pathlib import Path

from ..common.path_resolver import resolve_output_path, resolve_resource_base_path


@dataclass(slots=True)
class MultiPagePdfExportConfig:
    output_path: Path
    template_path: Path

    title: str
    author: str

    logo_path: Path | None = None
    # high dpi cause large export
    dpi: int = 150

    @classmethod
    def default(
        cls,
        output_path: str | Path,
        title: str,
        author: str,
        logo_path: str | Path | None,
    ) -> "MultiPagePdfExportConfig":
        resource_base = resolve_resource_base_path(__file__)
        output_path_obj, template_path = resolve_output_path(
            output_path, "Rapport_cartographique_multipage_{timestamp}.pdf", resource_base
        )

        return cls(
            output_path=output_path_obj,
            template_path=template_path,
            title=title,
            author=author,
            logo_path=Path(logo_path) if logo_path else None,
        )

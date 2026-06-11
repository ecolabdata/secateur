from dataclasses import dataclass
from pathlib import Path

from ..common.path_resolver import resolve_legend_output_path, resolve_resource_base_path


@dataclass(slots=True)
class LegendExportConfig:
    """Configuration for legend export."""

    output_path: Path
    template_path: Path
    layer_names: list[str]
    title: str
    author: str
    logo_path: Path | None = None
    dpi: int = 300
    max_legend_items_per_page: int = 20

    @classmethod
    def default(
        cls,
        *,
        output_path: str | Path,
        layer_names: list[str],
        title: str = "Légende",
        author: str = "QGIS User",
        logo_path: str | Path | None = None,
        max_legend_items_per_page: int = 20,
    ) -> "LegendExportConfig":
        """Create a default configuration.

        Resolves the output path (adds timestamped filename if a directory is given),
        sets the template path to the bundled legend layout, and normalises the logo path.
        """
        resource_base = resolve_resource_base_path(__file__)
        output_path_obj, template_path = resolve_legend_output_path(
            output_path, "Legende_{timestamp}.pdf", resource_base
        )

        return cls(
            output_path=output_path_obj,
            template_path=template_path,
            layer_names=layer_names,
            title=title,
            author=author,
            logo_path=Path(logo_path) if logo_path else None,
            max_legend_items_per_page=max_legend_items_per_page,
        )

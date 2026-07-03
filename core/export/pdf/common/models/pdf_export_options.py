from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PdfExportOptions:
    """Shared PDF export options for all export configurations."""

    output_path: Path
    template_path: Path
    dpi: int = 300
    page_size: str = "A4"
    force_vector_output: bool = True
    export_layers_as_vectors: bool = True
    export_metadata: bool = True
    rasterize_whole_image: bool = True

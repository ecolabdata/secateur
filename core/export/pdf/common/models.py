from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LayoutMetadata:
    title: str
    author: str
    date_text: str
    logo_path: Path | None = None
    page_text: str | None = None


@dataclass(slots=True)
class PdfExportOptions:
    dpi: int = 300
    write_geopdf: bool = False
    force_vector_output: bool = True
    export_layers_as_vectors: bool = True
    export_metadata: bool = True

from pathlib import Path
from tempfile import TemporaryDirectory

from qgis.core import QgsProject

from ..common.models import PdfExportOptions
from ..common.pdf_export import export_layout_to_pdf
from .config import LegendExportConfig
from .layout import build_legend_layout
from .pagination import LegendItemCounter, LegendPaginationService


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> None:
    """Merges individual PDF pages into a single PDF."""

    try:
        from pypdf import PdfWriter  # type: ignore
    except ImportError:
        import sys
        from pathlib import Path

        # Compute the repository root's vendor directory relative to this file
        repo_root = Path(__file__).resolve().parents[4]
        vendor = repo_root / "vendor"
        sys.path.insert(0, str(vendor))

        from pypdf import PdfWriter  # type: ignore

    writer = PdfWriter()
    for pdf_path in pdf_paths:
        writer.append(str(pdf_path))
    with open(output_path, "wb") as f:
        writer.write(f)
    writer.close()


class LegendExportService:
    """Orchestrates legend export across paginated layouts."""

    def __init__(self, project: QgsProject, config: LegendExportConfig) -> None:
        self.project = project
        self.config = config
        self.counter = LegendItemCounter()
        self.paginator = LegendPaginationService(
            project=project,
            counter=self.counter,
            max_items_per_page=config.max_legend_items_per_page,
        )

    def export(self) -> str:
        pages = self.paginator.paginate(self.config.layer_names)
        options = PdfExportOptions(
            dpi=self.config.dpi,
            write_geopdf=False,
            force_vector_output=False,
            export_layers_as_vectors=False,
            export_metadata=False,
        )
        with TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            page_paths: list[Path] = []
            for index, page in enumerate(pages, start=1):
                layout = build_legend_layout(
                    project=self.project,
                    template_path=self.config.template_path,
                    layer_names=page.layer_names,
                    title=self.config.title,
                    author=self.config.author,
                    logo_path=self.config.logo_path,
                    page_number=index,
                    total_pages=len(pages),
                )
                page_path = tmp_dir_path / f"legend_page_{index:03d}.pdf"
                export_layout_to_pdf(
                    layout=layout,
                    output_path=page_path,
                    options=options,
                )
                page_paths.append(page_path)
            merge_pdfs(page_paths, self.config.output_path)
        return str(self.config.output_path)

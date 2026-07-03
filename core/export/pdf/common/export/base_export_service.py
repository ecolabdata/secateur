"""
Improved base export service with collaborators.
This service delegates specific responsibilities to collaborators to reduce coupling
and improve testability.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory

from ..models import PdfExportOptions
from .collaborators import ExportLifecycle, LayoutFactory, LayoutStabilizer, PdfExporter, PdfMergerInterface


class BasePdfExportService(ABC):
    """Base service for PDF exports that delegates responsibilities to collaborators."""

    def __init__(
        self,
        layout_factory: LayoutFactory,
        exporter: PdfExporter,
        pdf_merger: PdfMergerInterface,
        lifecycle: ExportLifecycle,
        stabilizer: LayoutStabilizer,
    ):
        self.layout_factory = layout_factory
        self.exporter = exporter
        self.pdf_merger = pdf_merger
        self.lifecycle = lifecycle
        self.stabilizer = stabilizer

    @property
    @abstractmethod
    def output_path(self) -> Path:
        """Path where the final PDF will be written."""
        pass

    @property
    @abstractmethod
    def export_options(self) -> PdfExportOptions:
        """Export options for PDF generation."""
        pass

    def export(self) -> str:
        """Execute the export process using collaborators."""
        layouts = self.layout_factory.create_layouts()

        with TemporaryDirectory() as tmp_dir:
            pdfs = []

            for page_number, layout in enumerate(layouts, start=1):
                # Stabilize layout before export to ensure proper rendering
                self.stabilizer.stabilize(layout)

                path = Path(tmp_dir) / f"page_{page_number:03d}.pdf"

                self.exporter.export(
                    layout=layout,
                    output_path=path,
                    options=self.export_options,
                )

                pdfs.append(path)

            if len(pdfs) == 1:
                pdfs[0].replace(self.output_path)

            else:
                self.pdf_merger.merge(
                    pdf_paths=pdfs,
                    output_path=self.output_path,
                )

        # Finalize the export cycle to ensure cleanup
        self.lifecycle.finalize()

        return str(self.output_path)

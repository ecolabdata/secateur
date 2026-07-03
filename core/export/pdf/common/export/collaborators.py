"""
Collaborators for PDF export services.
These are responsible for specific aspects of the export process to decouple
the base service from implementation details.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from qgis.core import QgsPrintLayout

from ..lifecycle.cleanup import finalize_export_cycle
from ..lifecycle.refresh import stabilize_layout
from ..models import PdfExportOptions
from ..pdf_export import export_layout_to_pdf
from .pdf_merger import PdfMerger


class ExportLifecycle(ABC):
    """Interface for managing export lifecycle operations."""

    @abstractmethod
    def finalize(self) -> None:
        """Finalize the export cycle."""
        pass


class LayoutFactory(ABC):
    """Interface for creating layouts for export."""

    @abstractmethod
    def create_layouts(self) -> list[QgsPrintLayout]:
        """Create the layouts to be exported."""
        pass


class PdfExporter(ABC):
    """Interface for exporting layouts to PDF."""

    @abstractmethod
    def export(self, layout: QgsPrintLayout, output_path: Path, options: PdfExportOptions) -> Path:
        """Export a single layout to PDF."""
        pass


class PdfMergerInterface(ABC):
    """Interface for merging multiple PDF files."""

    @abstractmethod
    def merge(self, pdf_paths: list[Path], output_path: Path) -> None:
        """Merge multiple PDF files into one."""
        pass


class LayoutStabilizer(ABC):
    """Interface for stabilizing layouts before export."""

    @abstractmethod
    def stabilize(self, layout: QgsPrintLayout) -> None:
        """Stabilize a layout before export."""
        pass


class DefaultPdfExporter(PdfExporter):
    """Default implementation of PDF export functionality."""

    def export(self, layout: QgsPrintLayout, output_path: Path, options: PdfExportOptions) -> Path:
        """Export a single layout to PDF."""
        return export_layout_to_pdf(layout=layout, output_path=output_path, options=options)


class DefaultPdfMerger(PdfMergerInterface):
    """Default implementation of PDF merging functionality."""

    def merge(self, pdf_paths: list[Path], output_path: Path) -> None:
        """Merge multiple PDF files into one."""
        PdfMerger.merge(pdf_paths=pdf_paths, output_path=output_path)


class DefaultExportLifecycle(ExportLifecycle):
    """Default implementation of export lifecycle management."""

    def finalize(self) -> None:
        """Finalize the export cycle."""
        finalize_export_cycle()


class DefaultLayoutFactory(LayoutFactory):
    """Default implementation that creates layouts."""

    def __init__(self, layouts: list[QgsPrintLayout]):
        self.layouts = layouts

    def create_layouts(self) -> list[QgsPrintLayout]:
        """Create the layouts to be exported."""
        return self.layouts


class DefaultLayoutStabilizer(LayoutStabilizer):
    """Default implementation of layout stabilization."""

    def stabilize(self, layout: QgsPrintLayout) -> None:
        """Stabilize a layout before export."""
        stabilize_layout(layout)

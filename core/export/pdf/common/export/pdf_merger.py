from pathlib import Path

try:
    from pypdf import PdfWriter  # type: ignore
except ImportError:
    import sys
    from pathlib import Path

    # Compute the repository root's vendor directory relative to this file
    repo_root = Path(__file__).resolve().parents[5]
    vendor = repo_root / "vendor"
    sys.path.insert(0, str(vendor))

    from pypdf import PdfWriter  # type: ignore


class PdfMerger:
    """Merge multiple single-page PDF files into one output PDF."""

    @staticmethod
    def merge(
        pdf_paths: list[Path],
        output_path: Path,
    ) -> None:
        """Merge *pdf_paths*, in order, into a single PDF at *output_path*.

        Args:
            pdf_paths: Paths of the source PDF files, in the order they
                should appear in the merged document.
            output_path: Path where the merged PDF is written.
        """
        writer = PdfWriter()

        for pdf in pdf_paths:
            writer.append(str(pdf))

        with open(output_path, "wb") as f:
            writer.write(f)

        writer.close()

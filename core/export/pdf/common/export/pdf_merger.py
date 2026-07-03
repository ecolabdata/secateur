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
    @staticmethod
    def merge(
        pdf_paths: list[Path],
        output_path: Path,
    ) -> None:
        writer = PdfWriter()

        for pdf in pdf_paths:
            writer.append(str(pdf))

        with open(output_path, "wb") as f:
            writer.write(f)

        writer.close()

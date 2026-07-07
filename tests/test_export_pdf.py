"""Smoke tests for the PDF export flows (requires a real QGIS via pytest-qgis).

These only assert that a non-empty PDF file is produced end-to-end
(template loading, layout rendering, export, merge-if-needed). They do
not inspect the PDF's rendered content — that would need a much heavier
setup (rasterizing pages, comparing against reference images) that is out
of scope for this first pass. See core/export/pdf/AGENT.md for the
architecture these flows go through.
"""

from pathlib import Path

from qgis.core import QgsCoordinateReferenceSystem, QgsProject
from secateur.core.export.pdf.legend import export_legend
from secateur.core.export.pdf.multi_pdf import export_results_to_multi_page_pdf


def test_export_legend_produces_a_pdf(make_layer, tmp_path):
    layer = make_layer("Point", "My Points", [("POINT(0 0)", {"name": "a"})])
    QgsProject.instance().addMapLayer(layer)

    output_path = export_legend(
        output_path=tmp_path / "legend.pdf",
        layer_names=[layer.name()],
        title="Test Legend",
        author="pytest",
    )

    result = Path(output_path)
    assert result.exists()
    assert result.stat().st_size > 0


def test_export_multi_page_pdf_produces_a_pdf(make_layer, tmp_path):
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    layer = make_layer("Point", "Result", [("POINT(0 0)", {"name": "a"})])
    project.addMapLayer(layer)

    output_path = export_results_to_multi_page_pdf(
        [layer],
        str(tmp_path / "report.pdf"),
        logo_path="",
        author="pytest",
        title="Test Report",
    )

    result = Path(output_path)
    assert result.exists()
    assert result.stat().st_size > 0

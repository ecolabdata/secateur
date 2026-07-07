"""Tests for core.export.csv.export (requires a real QGIS via pytest-qgis)."""

import csv
from pathlib import Path

from qgis.core import QgsRasterLayer
from secateur.core.export.csv.export import export_results_to_csv


def test_export_results_to_csv_writes_one_file_per_vector_layer(make_layer, tmp_path):
    layer = make_layer(
        "Point",
        "My Layer",
        [("POINT(0 0)", {"name": "a"}), ("POINT(1 1)", {"name": "b"})],
    )

    written = export_results_to_csv([layer], str(tmp_path))

    assert len(written) == 1
    csv_path = Path(written[0])
    assert csv_path.name == "My Layer.csv"

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["name"]
    assert rows[1:] == [["a"], ["b"]]


def test_export_results_to_csv_skips_non_vector_layers(tmp_path):
    raster = QgsRasterLayer("", "not-a-vector")

    written = export_results_to_csv([raster], str(tmp_path))

    assert written == []


def test_export_results_to_csv_creates_output_dir(make_layer, tmp_path):
    layer = make_layer("Point", "l", [("POINT(0 0)", {"name": "a"})])
    output_dir = tmp_path / "does" / "not" / "exist"

    written = export_results_to_csv([layer], str(output_dir))

    assert output_dir.exists()
    assert len(written) == 1

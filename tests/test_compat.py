"""Tests for compat.py (requires a real QGIS via pytest-qgis).

The dev environment for this project is QGIS 3.34, which bundles Qt5, so
only the Qt5 branch of compat.py can actually be exercised here. The
Qt6/QGIS4 branch cannot be verified without a real QGIS4 install - the
corresponding test below is skipped rather than silently passing, so a
skip in the test report is an honest "not verified on this run", not a
false positive.
"""

import pytest
from qgis.PyQt.QtCore import QT_VERSION_STR, Qt
from secateur import compat


def test_qt_major_matches_actual_qt_version():
    assert int(QT_VERSION_STR.split(".")[0]) == compat.QT_MAJOR


@pytest.mark.skipif(compat.QT_MAJOR >= 6, reason="this environment runs Qt6, not Qt5")
def test_rich_text_alias_under_qt5():
    assert compat.RichText == Qt.RichText


@pytest.mark.skipif(compat.QT_MAJOR < 6, reason="requires a real QGIS4/Qt6 install to verify")
def test_rich_text_alias_under_qt6():
    assert compat.RichText == Qt.TextFormat.RichText

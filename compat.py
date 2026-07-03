"""
Qt5 / Qt6 compatibility layer.

Only expose API that differs between Qt5 and Qt6.

Add new aliases here as needed.
"""

from qgis.PyQt.QtCore import QT_VERSION_STR, Qt

QT_MAJOR = int(QT_VERSION_STR.split(".")[0])

if QT_MAJOR >= 6:
    RichText = Qt.TextFormat.RichText
    ...
else:
    RichText = Qt.RichText
    ...

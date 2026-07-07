import os

from qgis.PyQt.QtCore import QFile  # noqa: UP035


def _icons_dir() -> str:
    """Return the absolute path to the plugin's resources directory located at the project root."""
    basepath = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir))
    return os.path.join(basepath, "resources").replace("\\", "/")


def get_icon_path(icon_name: str) -> str:
    """Return the full path to an icon if it exists, otherwise an empty string."""
    path = os.path.join(_icons_dir(), icon_name)
    return path if QFile.exists(path) else ""

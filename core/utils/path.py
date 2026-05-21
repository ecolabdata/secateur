import os

from qgis.PyQt.QtCore import QFile  # noqa: UP035

from ..logger import logger


def _icons_dir():
    """Return the absolute path to the plugin's resources directory located at the project root."""
    # The file ``geopdf_utils.py`` resides in the ``core`` subdirectory;
    # the ``resources`` folder is at the repository root
    basepath = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
    return os.path.join(basepath, "resources").replace("\\", "/")


def get_icon_path(icon_name):
    """Return the full path to an icon if it exists, otherwise an empty string."""
    path = os.path.join(_icons_dir(), icon_name)
    return path if QFile.exists(path) else ""


def resolve_output_path(output_path: str) -> tuple[str, str]:
    """Resolve the final PDF path and a timestamp string.

    If *output_path* is a directory, a filename ``Rapport_cartographique_<timestamp>.pdf``
    is created inside it. Otherwise *output_path* is returned unchanged.
    """
    try:
        if os.path.isdir(output_path):
            from .formatting import timestamp_str

            date_hm = timestamp_str()
            filename = f"Rapport_cartographique_{date_hm}.pdf"
            full_path = os.path.join(output_path, filename)
        else:
            full_path = output_path
            from .formatting import timestamp_str

            date_hm = timestamp_str()
        return full_path, date_hm
    except Exception as e:
        logger.error(f"Failed to resolve output path '{output_path}': {e}")
        raise

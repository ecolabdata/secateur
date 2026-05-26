"""Formatting utilities extracted from...utils.
Provides:
- timestamp_str: current datetime formatted for filenames.
- _format_value: safely format QGIS attribute values.
- _safe_filename: sanitise a string for use as a filename.
"""

import re
from datetime import datetime
from typing import Any

from qgis.PyQt.QtCore import QDate, QDateTime, QTime  # noqa: UP035


def timestamp_str() -> str:
    """Return current datetime formatted as ``YYYY_MM_DD_HHh_MMin``.
    Centralises the timestamp format used for exported files.
    """
    return datetime.now().strftime("%Y_%m_%d_%Hh_%Mmin")


def display_date_str() -> str:
    """Renvoie la date courante au format « dd/mm/YYYY » utilisé dans les
    layouts (legende et GeoPDF)."""
    return datetime.now().strftime("%d/%m/%Y")


def _format_value(val: Any) -> str | Any:
    """Format various QGIS attribute values into string representations.

    Handles ``None`` (returns empty string) and QDate/QDateTime/QTime objects,
    converting them to ISO‑like strings. Other types are returned unchanged.
    """
    if val is None:
        return ""
    if isinstance(val, QDateTime):
        return val.toString("yyyy-MM-dd HH:mm:ss") if val.isValid() else ""
    if isinstance(val, QDate):
        return val.toString("yyyy-MM-dd") if val.isValid() else ""
    if isinstance(val, QTime):
        return val.toString("HH:mm:ss") if val.isValid() else ""
    return val


def _safe_filename(name: str) -> str:
    """Turn a layer name into a safe filename (no path separators, etc.)."""
    return re.sub(r"[^\w\s\-()]", "_", name).strip()

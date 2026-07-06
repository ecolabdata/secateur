"""
Base layout class that eliminates duplicated layout creation logic.

This class removes the duplicated create() method implementation that existed
in both legend/layout.py and multi_pdf/layout.py by providing a common
implementation that handles template loading and item extraction.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from qgis.core import QgsPrintLayout, QgsProject

from ...common.lifecycle.refresh import stabilize_layout

T = TypeVar("T", bound="BasePdfLayout")


class BasePdfLayout(ABC):
    """Abstract base class for all PDF layouts that handles common layout creation and management."""

    def __init__(self, layout: QgsPrintLayout) -> None:
        self._layout = layout

    @property
    def layout(self) -> QgsPrintLayout:
        """The underlying ``QgsPrintLayout`` instance."""
        return self._layout

    @classmethod
    @abstractmethod
    def create_layout(
        cls,
        *,
        project: QgsProject,
        template_path: Path,
        layout_name: str,
    ) -> QgsPrintLayout:
        """Load *template_path* into *project* as a new layout named *layout_name*.

        Args:
            project: QGIS project the layout is added to.
            template_path: Path to the ``.qpt`` template file to load.
            layout_name: Name assigned to the created layout.

        Returns:
            The newly created ``QgsPrintLayout``.
        """
        ...

    def stabilize(self) -> None:
        """Stabilize the layout before export."""
        stabilize_layout(self._layout)

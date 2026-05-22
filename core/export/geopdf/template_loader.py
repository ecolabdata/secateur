"""
Template loader utilities for GeoPDF export.
"""

from pathlib import Path

from qgis.core import QgsPrintLayout, QgsProject

from ...export.pdf.common.template_loader import create_layout_from_template


def load_layout_from_template(
    project: QgsProject,
    manager,
    template_path: str,
    layout_name: str,
) -> QgsPrintLayout:
    """Load a layout from a QPT template file."""
    layout_path = Path(template_path)
    layout = create_layout_from_template(
        project=project, template_path=layout_path, layout_name=layout_name, register_in_manager=True
    )
    return layout

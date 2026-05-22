"""
Common template loader utilities for PDF export.
"""

from pathlib import Path

from qgis.core import QgsPrintLayout, QgsProject, QgsReadWriteContext
from qgis.PyQt.QtXml import QDomDocument


def create_layout_from_template(
    *,
    project: QgsProject,
    template_path: Path,
    layout_name: str | None = None,
    register_in_manager: bool = False,
) -> QgsPrintLayout:
    """Load a layout from a QPT template file."""
    # Ensure any existing layout with the same name is removed to avoid stale references
    manager = project.layoutManager()
    if layout_name and manager.layoutByName(layout_name):
        manager.removeLayout(manager.layoutByName(layout_name))
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    if layout_name:
        layout.setName(layout_name)

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    with open(template_path, encoding="utf-8") as f:
        template_content = f.read()

    doc = QDomDocument()
    success, error_message, error_line, error_column = doc.setContent(template_content)

    if not success:
        raise ValueError(f"Failed to parse QPT template (line={error_line}, column={error_column}): {error_message}")

    context = QgsReadWriteContext()

    _, ok = layout.loadFromTemplate(doc, context)

    if not ok:
        raise RuntimeError(f"Failed to load layout template: {template_path}")

    if register_in_manager:
        manager = project.layoutManager()
        manager.addLayout(layout)

    # Retrieve the layout instance managed by the layout manager to ensure a valid Python wrapper
    if layout_name and register_in_manager:
        # Retrieve the layout instance from the manager to ensure it remains alive
        return manager.layoutByName(layout_name)

    return layout

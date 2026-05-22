"""
Template loader utilities for GeoPDF export.
"""

from qgis.core import QgsPrintLayout, QgsProject, QgsReadWriteContext
from qgis.PyQt.QtXml import QDomDocument


def load_layout_from_template(
    project: QgsProject,
    manager,
    template_path: str,
    layout_name: str,
) -> QgsPrintLayout:
    """Load a layout from a QPT template file."""
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)

    with open(template_path, encoding="utf-8") as f:
        template_content = f.read()

    doc = QDomDocument()
    success, error_message, error_line, error_column = doc.setContent(template_content)

    if not success:
        raise ValueError(f"Failed to parse QPT template (line={error_line}, column={error_column}): {error_message}")

    context = QgsReadWriteContext()

    items, ok = layout.loadFromTemplate(doc, context)

    if not ok:
        raise RuntimeError(f"Failed to load layout template: {template_path}")

    manager.addLayout(layout)

    # Retrieve the layout instance managed by the layout manager to ensure a valid Python wrapper
    return manager.layoutByName(layout_name)

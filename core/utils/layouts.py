"""Layout management helpers extracted from...utils.
Exports:
- clean_layouts
- create_layout
"""

from qgis.core import QgsLayoutManager, QgsPrintLayout, QgsProject


def clean_layouts(manager: QgsLayoutManager) -> None:
    """Remove all existing layouts to avoid C++ errors."""
    for layout in manager.printLayouts():
        manager.removeLayout(layout)


def create_layout(project: QgsProject, manager: QgsLayoutManager, name: str) -> QgsPrintLayout:
    """Create a new named ``QgsPrintLayout`` after removing any existing layout with the same name."""
    existing = manager.layoutByName(name)
    if existing:
        manager.removeLayout(existing)
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    manager.addLayout(layout)
    return layout

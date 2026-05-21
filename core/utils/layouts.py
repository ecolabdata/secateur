"""Layout management helpers extracted from core.utils.
Exports:
- clean_layouts
- create_layout
"""

from qgis.core import QgsPrintLayout


def clean_layouts(manager):
    """Remove all existing layouts to avoid C++ errors."""
    for layout in manager.printLayouts():
        manager.removeLayout(layout)


def create_layout(project, manager, name):
    """Create a new named ``QgsPrintLayout`` after removing any existing layout with the same name.
    """
    existing = manager.layoutByName(name)
    if existing:
        manager.removeLayout(existing)
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    manager.addLayout(layout)
    return layout

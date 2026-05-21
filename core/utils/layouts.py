"""Layout management helpers extracted from...utils.
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
    """Create a new named ``QgsPrintLayout`` after removing any existing layout with the same name."""
    existing = manager.layoutByName(name)
    if existing:
        manager.removeLayout(existing)
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    manager.addLayout(layout)
    return layout


def get_layout_item(layout: QgsPrintLayout, item_id: str):
    """Get a layout item by its ID, raising an error if not found."""
    item = layout.itemById(item_id)

    if item is None:
        raise ValueError(f"Layout item '{item_id}' not found")

    return item

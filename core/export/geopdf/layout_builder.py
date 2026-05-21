"""
Layout building orchestrator for GeoPDF export.
"""

from qgis.core import (
    QgsMapLayer,
    QgsPrintLayout,
    QgsProject,
    QgsRectangle,
)

from ...utils.formatting import timestamp_str
from .layout_populator import populate_layout_logo, populate_layout_texts
from .map_configurator import configure_layout_map

# Import extracted responsibilities
from .template_loader import load_layout_from_template


class GeoPdfLayoutBuilder:
    """Encapsulated builder for GeoPDF print layouts.

    Provides a clear, object‑oriented API with a single ``build`` method that
    returns a fully prepared :class:`QgsPrintLayout` instance.
    """

    def __init__(
        self,
        project: QgsProject,
        template_path: str,
        extent_rect: QgsRectangle,
        title: str,
        author: str,
        date_hm: str | None = None,
        logo_path: str | None = None,
        basemap_layer: QgsMapLayer | None = None,
    ) -> None:
        self.project = project
        self.template_path = template_path
        self.extent_rect = extent_rect
        self.title = title
        self.author = author
        self.logo_path = logo_path
        self.basemap_layer = basemap_layer
        self.manager = project.layoutManager()
        # Ensure a timestamp is present for layout naming and date field
        self.date_hm = date_hm or timestamp_str()

    def build(self) -> QgsPrintLayout:
        """Create the layout, configure it and return the prepared object."""
        layout_name = f"GeoPDF_{self.date_hm}"
        layout = load_layout_from_template(
            project=self.project,
            manager=self.manager,
            template_path=self.template_path,
            layout_name=layout_name,
        )
        self._configure_map(layout)
        layout.refresh()
        self._populate_metadata(layout)
        self._populate_logo(layout)
        layout.refresh()
        return layout

    def _configure_map(self, layout: QgsPrintLayout) -> None:
        """Configure the map item using the provided extent."""
        configure_layout_map(layout=layout, extent_rect=self.extent_rect)

    def _populate_metadata(self, layout: QgsPrintLayout) -> None:
        """Populate title, author and date text items."""
        populate_layout_texts(
            layout=layout,
            title=self.title,
            author=self.author,
            date_hm=self.date_hm,
        )

    def _populate_logo(self, layout: QgsPrintLayout) -> None:
        """Populate the logo picture item if a path is provided."""
        populate_layout_logo(layout=layout, logo_path=self.logo_path)


def build_report_layout(
    project: QgsProject,
    template_path: str,
    date_hm: str | None,
    extent_rect: QgsRectangle,
    logo_path: str | None,
    title: str,
    author: str,
    basemap_layer: QgsMapLayer | None,
) -> QgsPrintLayout:
    """Legacy wrapper preserving the original function signature.

    Internally delegates to :class:`GeoPdfLayoutBuilder` for the actual work.
    """
    builder = GeoPdfLayoutBuilder(
        project=project,
        template_path=template_path,
        extent_rect=extent_rect,
        title=title,
        author=author,
        date_hm=date_hm,
        logo_path=logo_path,
        basemap_layer=basemap_layer,
    )
    return builder.build()

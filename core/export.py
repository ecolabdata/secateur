import csv
import os
from contextlib import contextmanager

from qgis.core import (
    QgsLayoutExporter,
    QgsLayoutItemMap,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProcessingFeedback,
    QgsProject,
    QgsRectangle,
    QgsUnitTypes,
    QgsVectorLayer,
)

# Import helpers from geopdf_utils
from .geopdf_utils import (
    _add_frame_title,
    add_copyright,
    add_logo,
    add_map_credits,
    add_north_arrow,
    add_scale,
    add_title,
)
from .legend_exporter import export_legend
from .logger import logger
from .utils import (
    _format_value,
    _safe_filename,
    clean_layouts,
    create_layout,
    is_simple_fill,
    iterate_layers,
    set_layer_and_parents_visible,
    set_layer_opacity,
    temporary_visibility,
    timestamp_str,
)


def update_feedback(feedback: QgsProcessingFeedback | None, progress: int, message: str) -> None:
    """Convenient helper to update ``feedback`` if it is provided."""
    if feedback:
        feedback.setProgress(progress)
        feedback.pushInfo(message)


# ============================================================
# EXPORT CSV
# ============================================================


def export_results_to_csv(
    result_layers: list[QgsMapLayer],
    output_dir: str,
    feedback: QgsProcessingFeedback | None = None,
) -> list[str]:
    """Export each result layer as a separate CSV file inside output_dir.

    Creates output_dir if it doesn't exist. Returns the list of written file paths.
    progress.update(current, total, name) is called before each layer if a progress object is provided.
    """
    os.makedirs(output_dir, exist_ok=True)

    written = []

    def _write_csv(layer: QgsVectorLayer):
        """Callback used by :func:`iterate_layers` to write one CSV file.

        Non-vector layers are ignored.
        """
        if not isinstance(layer, QgsVectorLayer):
            return
        filename = _safe_filename(layer.name()) + ".csv"
        filepath = os.path.join(output_dir, filename)

        field_names = [field.name() for field in layer.fields()]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(field_names)
            for feat in layer.getFeatures():
                writer.writerow([_format_value(v) for v in feat.attributes()])

        written.append(filepath)

    iterate_layers(result_layers, _write_csv, feedback)
    # Ensure UI remains responsive during export
    from qgis.PyQt.QtWidgets import QApplication

    QApplication.processEvents()

    return written


# ============================================================
# EXPORT GEOPDF
# ============================================================


def resolve_output_path(output_path: str) -> tuple[str, str]:
    """Resolve the final PDF path and a timestamp string.

    If *output_path* is a directory, a filename ``Rapport_cartographique_<timestamp>.pdf``
    is created inside it. Otherwise *output_path* is returned unchanged.
    """
    try:
        if os.path.isdir(output_path):
            date_hm = timestamp_str()
            filename = f"Rapport_cartographique_{date_hm}.pdf"
            full_path = os.path.join(output_path, filename)
        else:
            full_path = output_path
            date_hm = timestamp_str()
        return full_path, date_hm
    except Exception as e:
        logger.error(f"Failed to resolve output path '{output_path}': {e}")
        raise


def get_source_vector_layer(result_layers: list[QgsMapLayer]) -> QgsVectorLayer:
    """Validate *result_layers* for PDF export.

    Raises ``ValueError`` if the list is empty and ``TypeError`` if the first
    element is not a ``QgsVectorLayer``.
    """
    if not result_layers:
        raise ValueError("result_layers must contain at least one layer for extent calculation")

    layer = result_layers[0]

    if not isinstance(layer, QgsVectorLayer):
        raise TypeError("First result layer must be a vector layer")

    return layer


def compute_export_extent(layer: QgsVectorLayer) -> QgsRectangle:
    """Return a buffered ``QgsRectangle`` covering *layer*.

    The rectangle is enlarged by 5 % of its width and height.
    """
    bbox = layer.extent()
    bbox.grow(bbox.width() * 0.05 + bbox.height() * 0.05)
    return QgsRectangle(bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum())


@contextmanager
def temporary_visible_layers(
    root, result_layers: list[QgsMapLayer], basemap_layer: QgsMapLayer | None, feedback: QgsProcessingFeedback | None
):
    """Temporarily hide all layers then make *result_layers* (and optional *basemap_layer*) visible.

    Yields the list of layer names used for the legend.
    """
    visible_count = 0
    # Hide everything via the existing ``temporary_visibility`` helper
    with temporary_visibility(root):

        def _make_visible(layer):
            nonlocal visible_count
            try:
                if is_simple_fill(layer):
                    set_layer_opacity(layer, opacity=0.8)
                visible_count += int(set_layer_and_parents_visible(root, layer))
            except Exception as exc:
                logger.exception("Could not set visibility for layer %s: %s", layer.name(), exc)

        iterate_layers(result_layers, _make_visible, feedback)
        if visible_count == 0:
            logger.warning("temporary_visible_layers: no result layers could be made visible")
        if basemap_layer is not None:
            try:
                visible_count += int(set_layer_and_parents_visible(root, basemap_layer))
            except Exception as exc:
                logger.exception("Could not set visibility for basemap layer %s: %s", basemap_layer.name(), exc)
        layer_names = [lyr.name() for lyr in result_layers]
        update_feedback(feedback, 20, "Couches de résultat rendues visibles")
        yield layer_names


def create_map_item(layout: QgsPrintLayout, extent_rect: QgsRectangle) -> QgsLayoutItemMap:
    """Create and configure the map item for the layout.

    Returns the configured ``QgsLayoutItemMap`` instance.
    """
    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(20, 20, 20, 20)
    map_item.setExtent(extent_rect)
    map_item.attemptMove(QgsLayoutPoint(5, 26, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(240, 180, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map_item)
    map_item.refresh()
    return map_item


def add_layout_decorations(
    layout,
    map_item: QgsLayoutItemMap,
    extent_rect: QgsRectangle,
    logo_path: str,
    title: str,
    author: str,
    basemap_layer: QgsMapLayer | None,
    feedback: QgsProcessingFeedback | None,
):
    """Add title, frame, scale bar, north arrow, logo and credits to the layout."""
    # Title and surrounding frame
    add_title(layout, title)
    _add_frame_title(layout, largeur_page=295.0)
    update_feedback(feedback, 60, "Titre et cadre ajoutés")
    # Decorations
    add_scale(layout, map_item, extent_rect)
    add_north_arrow(layout)
    add_logo(layout, logo_path)
    if author:
        add_copyright(layout, author=author)
    else:
        add_copyright(layout)
    if basemap_layer is not None:
        add_map_credits(layout, f"© {basemap_layer.name()}")
    update_feedback(feedback, 70, "Légende construite")


def build_report_layout(
    project: QgsProject,
    date_hm: str,
    extent_rect: QgsRectangle,
    logo_path: str,
    title: str,
    author: str,
    basemap_layer: QgsMapLayer | None,
    feedback: QgsProcessingFeedback | None,
) -> QgsPrintLayout:
    """Create the layout and populate it with map item and decorations.

    Returns the fully prepared ``QgsPrintLayout``.
    """
    manager = project.layoutManager()
    clean_layouts(manager)
    layout_name = f"GeoPDF_{date_hm}"
    layout = create_layout(project, manager, layout_name)
    update_feedback(feedback, 40, "Mise en page initialisée")
    # Map item
    map_item = create_map_item(layout, extent_rect)
    update_feedback(feedback, 50, "Élément carte ajouté")
    # Decorations and title/frame
    add_layout_decorations(layout, map_item, extent_rect, logo_path, title, author, basemap_layer, feedback)
    return layout


def export_results_to_pdf(
    result_layers: list[QgsMapLayer],
    output_path: str,
    logo_path: str,
    feedback: QgsProcessingFeedback | None = None,
    basemap_layer: QgsMapLayer | None = None,
    author: str = "",
    title: str = "Résultats Secateur",
):
    """Orchestrate PDF export using well‑separated helper functions."""
    # 1. Resolve output location
    full_path, date_hm = resolve_output_path(output_path)
    # 2. Validate inputs
    src_layer = get_source_vector_layer(result_layers)
    # 3. Compute extent from first result layer
    extent_rect = compute_export_extent(src_layer)
    # 4. Manage layer visibility and obtain legend names
    root = QgsProject.instance().layerTreeRoot()
    with temporary_visible_layers(root, result_layers, basemap_layer, feedback) as layer_names:
        # 5. Initialise feedback
        update_feedback(feedback, 0, "Préparation de l'export PDF…")
        # 6. Build layout
        project = QgsProject.instance()
        layout = build_report_layout(
            project,
            date_hm,
            extent_rect,
            logo_path,
            title,
            author,
            basemap_layer,
            feedback,
        )
        # 7. Export legend
        try:
            legend_output_path = os.path.join(os.path.dirname(full_path), f"Legende_GeoPDF_{date_hm}.pdf")
            export_legend(
                template_path=os.path.join(os.path.dirname(__file__), "../resources/legend_layout.qpt"),
                output_path=legend_output_path,
                layer_names=layer_names,
                logo_path=logo_path,
                title=title,
                author=author,
            )
        except Exception as e:
            logger.warning(f"External legend export failed: {e}")
        # 8. Export GeoPDF
        update_feedback(feedback, 80, "Export du GeoPDF en cours")
        exporter = QgsLayoutExporter(layout)
        exporter.layout().refresh()
        settings = QgsLayoutExporter.PdfExportSettings()
        settings.dpi = 300
        settings.writeGeoPdf = True
        settings.forceVectorOutput = True
        settings.exportLayersAsVectors = True
        settings.exportMetadata = True
        try:
            from qgis.PyQt.QtWidgets import QApplication

            QApplication.processEvents()
            exporter.exportToPdf(full_path, settings)
            QApplication.processEvents()
            update_feedback(feedback, 100, "Export terminé")
        except Exception as e:
            logger.error(f"GeoPDF export failed: {e}")
            raise RuntimeError(f"GeoPDF export failed: {e}") from e
    # Clean up any temporary layouts created during the context
    manager = QgsProject.instance().layoutManager()
    clean_layouts(manager)
    logger.info(f"GeoPDF exported to: {full_path}")
    return full_path

import csv
import os
from contextlib import contextmanager

from qgis.core import (
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsMapLayer,
    QgsPrintLayout,
    QgsProcessingFeedback,
    QgsProject,
    QgsReadWriteContext,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument

from .legend_exporter import export_legend
from .logger import logger
from .utils import (
    _format_value,
    _safe_filename,
    clean_layouts,
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

    return layout


def get_layout_item(layout: QgsPrintLayout, item_id: str):
    """Get a layout item by its ID, raising an error if not found."""
    item = layout.itemById(item_id)

    if item is None:
        raise ValueError(f"Layout item '{item_id}' not found")

    return item


def configure_layout_map(
    layout: QgsPrintLayout,
    extent_rect: QgsRectangle,
) -> None:
    """Configure the map item in the layout from template."""

    map_item = get_layout_item(layout, "Map 1")

    if not isinstance(map_item, QgsLayoutItemMap):
        raise TypeError(f"Layout item 'Map 1' is not a QgsLayoutItemMap, got {type(map_item)}")

    logger.info(
        "Applying export extent to map item: xmin=%s ymin=%s xmax=%s ymax=%s",
        extent_rect.xMinimum(),
        extent_rect.yMinimum(),
        extent_rect.xMaximum(),
        extent_rect.yMaximum(),
    )

    # ------------------------------------------------------------------
    # IMPORTANT:
    # The template map frame has its own aspect ratio.
    # We must adapt the geographic extent to that ratio,
    # otherwise QGIS expands the map unpredictably.
    # ------------------------------------------------------------------

    map_rect = map_item.rect()

    frame_width = map_rect.width()
    frame_height = map_rect.height()

    if frame_height == 0:
        raise ValueError("Map frame height is zero")

    frame_ratio = frame_width / frame_height

    extent_width = extent_rect.width()
    extent_height = extent_rect.height()

    if extent_height == 0:
        raise ValueError("Extent height is zero")

    extent_ratio = extent_width / extent_height

    adjusted_extent = QgsRectangle(extent_rect)

    # ------------------------------------------------------------------
    # Adjust extent to frame aspect ratio
    # ------------------------------------------------------------------

    if extent_ratio > frame_ratio:
        # extent too wide -> increase height
        new_height = extent_width / frame_ratio
        delta = (new_height - extent_height) / 2

        adjusted_extent.setYMinimum(extent_rect.yMinimum() - delta)
        adjusted_extent.setYMaximum(extent_rect.yMaximum() + delta)

    else:
        # extent too tall -> increase width
        new_width = extent_height * frame_ratio
        delta = (new_width - extent_width) / 2

        adjusted_extent.setXMinimum(extent_rect.xMinimum() - delta)
        adjusted_extent.setXMaximum(extent_rect.xMaximum() + delta)

    logger.info(
        "Adjusted extent: xmin=%s ymin=%s xmax=%s ymax=%s",
        adjusted_extent.xMinimum(),
        adjusted_extent.yMinimum(),
        adjusted_extent.xMaximum(),
        adjusted_extent.yMaximum(),
    )

    # ------------------------------------------------------------------
    # Reset inherited template state
    # ------------------------------------------------------------------

    map_item.setAtlasDriven(False)

    # Important with QPT templates
    map_item.setKeepLayerSet(False)
    map_item.setKeepLayerStyles(False)

    # ------------------------------------------------------------------
    # Apply corrected extent
    # ------------------------------------------------------------------

    map_item.zoomToExtent(adjusted_extent)

    # Force redraw
    map_item.refresh()
    map_item.invalidateCache()
    map_item.update()


def populate_layout_texts(
    layout: QgsPrintLayout,
    title: str,
    author: str,
    date_hm: str,
) -> None:
    """Populate text items in the layout with dynamic content."""
    # Title
    title_item = get_layout_item(layout, "title")
    if not isinstance(title_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'title' is not a QgsLayoutItemLabel, got {type(title_item)}")
    title_item.setText(title)
    title_item.refresh()

    # Author
    author_item = get_layout_item(layout, "author")
    if not isinstance(author_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'author' is not a QgsLayoutItemLabel, got {type(author_item)}")
    author_item.setText(author or "")
    author_item.refresh()

    # Date
    date_item = get_layout_item(layout, "date")
    if not isinstance(date_item, QgsLayoutItemLabel):
        raise TypeError(f"Layout item 'date' is not a QgsLayoutItemLabel, got {type(date_item)}")
    date_item.setText(date_hm)
    date_item.refresh()


def populate_layout_logo(
    layout: QgsPrintLayout,
    logo_path: str,
) -> None:
    """Populate the logo item in the layout with a dynamic logo."""
    logo_item = get_layout_item(layout, "logo")

    if not isinstance(logo_item, QgsLayoutItemPicture):
        raise TypeError(f"Layout item 'logo' is not a QgsLayoutItemPicture, got {type(logo_item)}")

    if logo_path and os.path.exists(logo_path):
        logo_item.setPicturePath(logo_path)
        logo_item.refresh()


def build_report_layout(
    project: QgsProject,
    template_path: str,
    date_hm: str,
    extent_rect: QgsRectangle,
    logo_path: str,
    title: str,
    author: str,
    basemap_layer: QgsMapLayer | None,
    feedback: QgsProcessingFeedback | None,
) -> QgsPrintLayout:
    """Create the layout from a QPT template and populate it with dynamic content.

    Returns the fully prepared ``QgsPrintLayout``.
    """
    manager = project.layoutManager()

    clean_layouts(manager)

    layout_name = f"GeoPDF_{date_hm}"

    layout = load_layout_from_template(
        project=project,
        manager=manager,
        template_path=template_path,
        layout_name=layout_name,
    )

    update_feedback(feedback, 40, "Template QPT chargé")

    configure_layout_map(
        layout=layout,
        extent_rect=extent_rect,
    )

    # Refresh layout to ensure map changes are applied
    layout.refresh()

    update_feedback(feedback, 50, "Carte configurée")

    populate_layout_texts(
        layout=layout,
        title=title,
        author=author,
        date_hm=date_hm,
    )

    update_feedback(feedback, 60, "Textes injectés")

    populate_layout_logo(
        layout=layout,
        logo_path=logo_path,
    )

    update_feedback(feedback, 70, "Logo injecté")

    layout.refresh()

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
        template_path = os.path.join(
            os.path.dirname(__file__),
            "../resources/report_page.qpt",
        )
        layout = build_report_layout(
            project=project,
            template_path=template_path,
            date_hm=date_hm,
            extent_rect=extent_rect,
            logo_path=logo_path,
            title=title,
            author=author,
            basemap_layer=basemap_layer,
            feedback=feedback,
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

        settings = QgsLayoutExporter.PdfExportSettings()
        settings.dpi = 300
        settings.writeGeoPdf = True
        settings.forceVectorOutput = True
        settings.exportLayersAsVectors = True
        settings.exportMetadata = True

        from qgis.PyQt.QtWidgets import QApplication

        try:
            # Ensure layout is fully refreshed before export
            layout.refresh()
            exporter.layout().refresh()

            QApplication.processEvents()

            result = exporter.exportToPdf(full_path, settings)

            QApplication.processEvents()

            if result != QgsLayoutExporter.Success:
                raise RuntimeError(f"PDF export failed with code: {result}")

            update_feedback(feedback, 100, "Export terminé")

        except Exception as e:
            logger.error(f"GeoPDF export failed: {e}")
            raise RuntimeError(f"GeoPDF export failed: {e}") from e
    # Clean up any temporary layouts created during the context
    manager = QgsProject.instance().layoutManager()
    clean_layouts(manager)
    logger.info(f"GeoPDF exported to: {full_path}")
    return full_path

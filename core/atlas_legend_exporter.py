from datetime import datetime

from qgis.core import QgsFeature, QgsGeometry, QgsLayoutExporter, QgsProject, QgsVectorLayer

from .logger import logger
from .utils import create_layout, timestamp_str


def export_legend_atlas(
    template_path: str,
    output_path: str,
    layer_names: list[str],
    logo_path: str | None = None,
    per_page: int = 25,
) -> str:
    """
    Export a legend using QGIS Atlas functionality instead of manual generation.

    This function creates an Atlas-driven legend PDF by:
    1. Loading the template file
    2. Creating a memory layer to serve as the Atlas coverage layer
    3. Using the template's Atlas settings to generate legend pages
    4. Replacing the Atlas coverage layer with our memory layer

    Parameters:
        template_path: Path to the QPT template file
        output_path: Output PDF file path
        layer_names: List of layer names to include in the legend
        logo_path: Optional logo path to override in template
        per_page: Number of layers per legend page

    Returns:
        The output path of the generated PDF

    Raises:
        ValueError: If required items (legend, title) are missing from template
        Exception: If export fails
    """
    logger.warning(f"layer_names count: {len(layer_names)}")
    logger.warning(f"layer_names sample: {layer_names[:5]}")
    # Load template layout
    project = QgsProject.instance()
    manager = project.layoutManager()
    layout_name = f"AtlasLegend_{timestamp_str()}"
    layout = create_layout(project, manager, layout_name)

    from qgis.core import QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument

    doc = QDomDocument()

    with open(template_path, encoding="utf-8") as f:
        doc.setContent(f.read())

    context = QgsReadWriteContext()

    layout.loadFromTemplate(
        doc,
        context,
        clearExisting=True,
    )

    # Retrieve template items (may be None if not present)
    legend_item = layout.itemById("legend")
    title_item = layout.itemById("title")
    author_item = layout.itemById("author")
    date_item = layout.itemById("date")
    logo_item = layout.itemById("logo") if logo_path else None

    # Validate required items
    if legend_item is None:
        raise ValueError("Required legend item with ID 'legend' not found in template")
    if title_item is None:
        raise ValueError("Required title item with ID 'title' not found in template")

    # Create a memory layer for Atlas coverage
    memory_layer = _create_memory_layer_for_atlas(layer_names, per_page)

    # Add memory layer to project and include it in the layer tree
    QgsProject.instance().addMapLayer(memory_layer, addToLegend=True)

    # Ensure layer is properly initialized before Atlas configuration
    memory_layer.updateFields()
    memory_layer.updateExtents()

    # Configure Atlas to use our memory layer
    atlas = layout.atlas()
    if atlas:
        # Set the Atlas coverage layer to our memory layer
        atlas.setCoverageLayer(memory_layer)

        # Make sure Atlas is enabled
        atlas.setEnabled(True)

        # Ensure Atlas features are properly filtered and updated
        atlas.setFilterFeatures(False)
        atlas.setSortFeatures(False)
        atlas.updateFeatures()
        atlas.first()
        atlas.refreshCurrentFeature()

        logger.warning(f"Atlas count after update: {atlas.count()}")


        # Log diagnostic info
        logger.warning(f"Atlas enabled: {atlas.enabled()}")
        logger.warning(f"Atlas feature count: {atlas.count()}")
        logger.warning(f"Memory layer feature count: {memory_layer.featureCount()}")
        logger.warning(f"Memory layer provider feature count: {memory_layer.dataProvider().featureCount()}")

    # Ensure legend item is visible for Atlas rendering
    if legend_item:
        legend_item.setVisible(True)

    # Set up title, author, date, and logo items if they exist
    _setup_static_items(layout, title_item, author_item, date_item, logo_item, logo_path)

    # Export to PDF
    try:
        _export_layout_to_pdf(layout, output_path)
    finally:
        # Clean up temporary layout and memory layer
        manager.removeLayout(layout)
        # Remove the memory layer from project
        QgsProject.instance().removeMapLayer(memory_layer.id())

    return output_path


def _create_memory_layer_for_atlas(layer_names: list[str], per_page: int = 25) -> QgsVectorLayer:
    layer = QgsVectorLayer(
        "Polygon?crs=EPSG:4326",
        "legend_atlas",
        "memory",
    )

    provider = layer.dataProvider()

    from qgis.PyQt.QtCore import QVariant
    from qgis.core import QgsField

    provider.addAttributes([
        QgsField("id", QVariant.Int),
        QgsField("page", QVariant.Int),
        QgsField("layer_names", QVariant.String),
    ])

    layer.updateFields()

    chunks = list(_chunk_layers(layer_names, per_page))

    features = []

    for page_index, chunk in enumerate(chunks):

        feature = QgsFeature()

        feature.setFields(layer.fields())

        feature.setGeometry(
            QgsGeometry.fromWkt(
                "POLYGON((0 0,0 1,1 1,1 0,0 0))"
            )
        )

        feature["id"] = page_index + 1
        feature["page"] = page_index + 1
        feature["layer_names"] = "; ".join(chunk)

        features.append(feature)

    ok, added = provider.addFeatures(features)

    logger.warning(f"addFeatures ok={ok}")
    logger.warning(f"added count={len(added)}")

    layer.updateExtents()
    layer.triggerRepaint()

    logger.warning(
        f"Created atlas layer with {layer.featureCount()} features"
    )

    # Diagnostic: Print feature IDs to verify features were added
    for f in layer.getFeatures():
        logger.warning(f"feature id={f['id']}")

    return layer


def _chunk_layers(layer_names, per_page=25):
    """Chunk layer names into groups of per_page size."""
    for i in range(0, len(layer_names), per_page):
        yield layer_names[i : i + per_page]


def _setup_static_items(layout, title_item, author_item, date_item, logo_item, logo_path):
    """Setup the static items (title, author, date, logo) in the layout."""
    # Set up title with dynamic content
    if title_item:
        # Set visibility to True to make title appear
        title_item.setVisible(True)

    # Set up author
    if author_item:
        author_item.setText("Auteur: QGIS User")
        author_item.setVisible(True)

    # Set up date
    if date_item:
        date_item.setText(datetime.now().strftime("%d/%m/%Y"))
        date_item.setVisible(True)

    # Set up logo
    if logo_item and logo_path:
        logo_item.setPicturePath(logo_path)
        logo_item.setVisible(True)


def _export_layout_to_pdf(layout, path):
    """Export the layout to PDF."""
    exporter = QgsLayoutExporter(layout)

    settings = QgsLayoutExporter.PdfExportSettings()
    settings.dpi = 300

    atlas = layout.atlas()

    if atlas and atlas.enabled():
        result, error = exporter.exportToPdf(
            atlas,
            path,
            settings,
        )
    else:
        result = exporter.exportToPdf(
            path,
            settings,
        )
        error = ""

    logger.warning(f"Export result: {result}, error={error}")

    if result != QgsLayoutExporter.Success:
        raise Exception(
            f"PDF export failed with code={result}, error={error}"
        )
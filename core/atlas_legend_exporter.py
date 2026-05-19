import os
from datetime import datetime
from typing import List, Optional

from qgis.core import (
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemPicture,
    QgsLayoutItemLegend,
    QgsLayoutItemPage,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsProject,
    QgsRectangle,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry
)

from .utils import create_layout, clean_layouts, timestamp_str


def export_legend_atlas(
    template_path: str,
    output_path: str,
    layer_names: List[str],
    logo_path: Optional[str] = None,
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
    
    # Add memory layer to project but make sure it's not in the layer tree
    QgsProject.instance().addMapLayer(memory_layer, False)
    
    # Configure Atlas to use our memory layer
    atlas = layout.atlas()
    if atlas:
        # Set the Atlas coverage layer to our memory layer
        atlas.setCoverageLayer(memory_layer)
        
        # Make sure Atlas is enabled
        atlas.setEnabled(True)
    
    # Remove the dummy legend element since Atlas will handle it
    if legend_item:
        layout.removeLayoutItem(legend_item)
    
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


def _create_memory_layer_for_atlas(layer_names: List[str], per_page: int = 25) -> QgsVectorLayer:
    """Create a memory layer with features for each page of the legend."""
    # Create a memory layer with the required fields
    layer = QgsVectorLayer(
        "Point?crs=EPSG:4326&field=id:integer&field=page:integer&field=layer_names:string",
        "legend_atlas",
        "memory",
    )
    # Ensure fields are loaded
    layer.updateFields()

    # Create features for each page
    features = []
    chunks = list(_chunk_layers(layer_names, per_page))

    for page_index, chunk in enumerate(chunks):
        # Initialize feature with the layer's fields
        feature = QgsFeature(layer.fields())
        # Use a simple dummy point geometry (required but not used by Atlas)
        feature.setGeometry(QgsGeometry.fromWkt("POINT (0 0)"))
        # Set attribute values
        feature["id"] = page_index + 1
        feature["page"] = page_index + 1
        feature["layer_names"] = "; ".join(chunk)
        features.append(feature)

    # Add features to the layer
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
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

    exporter.exportToPdf(path, settings)
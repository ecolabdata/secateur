from qgis.core import QgsLayerTreeLayer
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QComboBox

from ...core.constants import BASEMAP_GROUP_NAME
from ...core.utils.layers import find_group, get_basemap_group


class BasemapComboBox(QComboBox):
    """Combo box listing layers contained in the 'Fonds de carte' group.

    The content is refreshed every time the popup is opened in order to
    reflect the current state of the QGIS project.

    The first item is always "Aucun fond de carte".
    """

    EMPTY_TEXT = "Aucun fond de carte"

    basemapGroupCreated = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Default state before first interaction.
        self.addItem(self.EMPTY_TEXT, None)

    def showPopup(self) -> None:
        """Refresh the layer list from the basemap group before showing the popup."""
        self._reload()
        super().showPopup()

    def selected_layer_id(self) -> str | None:
        """Return currently selected layer id."""
        return self.currentData()

    def _reload(self) -> None:
        """Reload available basemap layers from the dedicated group."""
        current_layer_id = self.currentData()

        self.blockSignals(True)

        try:
            group_existed = find_group([BASEMAP_GROUP_NAME]) is not None

            group = get_basemap_group()

            self.clear()

            # Always keep the empty choice.
            self.addItem(self.EMPTY_TEXT, None)

            group = get_basemap_group()

            if group is not None:
                for child in group.children():
                    if not isinstance(child, QgsLayerTreeLayer):
                        continue

                    layer = child.layer()

                    if layer is None:
                        continue

                    self.addItem(
                        layer.name(),
                        layer.id(),
                    )

            # Restore previous selection if still available.
            index = self.findData(current_layer_id)

            if index >= 0:
                self.setCurrentIndex(index)
            else:
                self.setCurrentIndex(0)

        finally:
            self.blockSignals(False)

            if not group_existed:
                self.basemapGroupCreated.emit()

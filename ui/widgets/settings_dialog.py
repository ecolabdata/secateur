from typing import Any

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.image_manager import ImageManager
from ..settings import SettingsManager


class SettingsDialog(QDialog):
    """Dialog for editing the plugin's author and logo settings."""

    def __init__(self, settings: SettingsManager, image_manager: ImageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings = settings
        self.image_manager = image_manager

        self.setWindowTitle("Paramètres")

        layout = QVBoxLayout(self)

        # ───────── Auteur ─────────
        layout.addWidget(QLabel("Auteur :"))
        self.author_input = QLineEdit(self.settings.author)
        layout.addWidget(self.author_input)

        # ───────── Logo ─────────
        layout.addWidget(QLabel("Logo :"))

        row = QHBoxLayout()

        self.logo_label = QLabel(self._display_logo_name(self.settings.logo_path))
        row.addWidget(self.logo_label)

        self.logo_button = QPushButton("Choisir…")
        self.logo_button.clicked.connect(self._select_logo)
        row.addWidget(self.logo_button)

        layout.addLayout(row)

        self.logo_display = QLabel()
        self.logo_display.setFixedSize(120, 120)
        self.logo_display.setStyleSheet("border: 1px solid #ccc;")
        self.logo_display.setScaledContents(True)
        self.logo_display.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.logo_display)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

        self._selected_logo = None
        self._set_logo_display(self.settings.logo_path)

    def _select_logo(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un logo",
            "",
            "Images (*.png *.jpg *.jpeg *.svg)",
        )

        if not file_path:
            return

        try:
            self.image_manager.validate_image(file_path)
            self._selected_logo = file_path
            self.logo_label.setStyleSheet("")
            self.logo_label.setText(self._display_logo_name(file_path))
            self._set_logo_display(file_path)

        except Exception as err:
            self.logo_label.setStyleSheet("color: red;")
            self.logo_label.setText(f"{str(err)}")
            self._selected_logo = None

    def get_values(self) -> dict[str, Any]:
        """Return the edited ``author`` and ``logo`` (path or ``None``) values."""
        return {
            "author": self.author_input.text().strip(),
            "logo": self._selected_logo,
        }

    def _display_logo_name(self, path: str) -> str:
        return path.split("/")[-1] if path else "Aucun logo"

    def _set_logo_display(self, path: str):
        pixmap = QPixmap(path)

        if pixmap.isNull():
            self.logo_display.clear()
            return

        scaled = pixmap.scaled(
            self.logo_display.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.logo_display.setPixmap(scaled)

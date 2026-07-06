from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from qgis.core import QgsMapLayer, QgsProcessingFeedback, QgsVectorLayer
from qgis.PyQt.QtCore import Qt, QTimer, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..compat import RichText
from ..core.constants import BASEMAP_GROUP_NAME
from ..core.export import export_legend, export_results_to_csv, export_results_to_multi_page_pdf
from ..core.image_manager import ImageManager
from ..core.logger import logger
from ..core.utils.layer_resolver import LayerResolver
from .service import ProcessResult, SecateurService
from .settings import SettingsManager
from .widgets.basemap_combo import BasemapComboBox
from .widgets.settings_dialog import SettingsDialog


@runtime_checkable
class QgisInterfaceProtocol(Protocol):
    def mainWindow(self) -> QWidget: ...
    def activeLayer(self) -> Any: ...


@contextmanager
def wait_cursor():
    """Push a waiting cursor and guarantee its restoration.

    Uses Qt's override‑cursor stack; the cursor is restored even if the
    surrounding block raises or returns early.
    """
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


# ──────────────────────────────────────────────
#  State object with explicit invariants
# ──────────────────────────────────────────────


@dataclass
class _SecateurState:
    # Invariant:
    # - None before valid selection
    # - layer ID after _handle_selection if success
    selected_layer_id: str | None = None

    # Invariant:
    # - always a list (never None)
    # - contains only layer IDs
    result_layer_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        assert isinstance(self.result_layer_ids, list)


class SecateurPanel(QDockWidget):
    def __init__(self, iface: QgisInterfaceProtocol, parent: QWidget | None = None) -> None:
        super().__init__("Sécateur", parent or iface.mainWindow())
        self.iface = iface

        self.settings = SettingsManager()
        self.image_manager = ImageManager()
        self.state = _SecateurState()
        self.service = SecateurService()

        self._feedback: QgsProcessingFeedback | None = None

        self._build_ui()

    # UI construction identical (unchanged)
    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        first_label = QLabel()
        first_label.setText(
            '1. Sélectionner la géométrie de référence pour l\'intersection<br>\
            <a href="https://docs.qgis.org/3.34/fr/docs/user_manual/introduction/general_tools.html#sec-selection"\
            style="color: blue;">Comment faire ?</a><br><br>\
            2. Intersecter les couches'
        )
        first_label.setOpenExternalLinks(True)
        first_label.setTextFormat(RichText)
        layout.addWidget(first_label)

        btn_row = QHBoxLayout()
        self.run_button = QPushButton("Réaliser l'intersection")
        self.run_button.clicked.connect(self._execute)
        btn_row.addWidget(self.run_button)
        layout.addLayout(btn_row)

        options_row = QHBoxLayout()
        self.raster_checkbox = QCheckBox("Inclure les couches rasters")
        self.raster_checkbox.setChecked(self.settings.include_raster)
        self.raster_checkbox.stateChanged.connect(self._on_include_raster_changed)
        options_row.addWidget(self.raster_checkbox)
        layout.addLayout(options_row)

        layout.addWidget(QLabel("3. Exporter les résultats"))

        pdf_frame = QFrame()
        pdf_frame.setFrameShape(QFrame.StyledPanel)
        pdf_layout = QVBoxLayout(pdf_frame)

        pdf_title_label = QLabel("Export PDF")
        pdf_title_label.setStyleSheet("font-weight: bold;")
        pdf_layout.addWidget(pdf_title_label)

        pdf_layout.addWidget(QLabel("Choisir un fond de carte (facultatif) :"))

        self.basemap_combo = BasemapComboBox()
        pdf_layout.addWidget(self.basemap_combo)

        pdf_layout.addWidget(QLabel("Modifier le titre du rapport :"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Titre du PDF")
        self.title_input.setText(self.settings.pdf_title)
        pdf_layout.addWidget(self.title_input)

        pdf_row = QHBoxLayout()

        self.export_pdf_button = QPushButton("Exporter le PDF et sa légende")
        self.export_pdf_button.clicked.connect(self._on_export_pdf)
        pdf_row.addWidget(self.export_pdf_button)

        self.edit_settings_button = QPushButton("Paramètres…")
        self.edit_settings_button.clicked.connect(self._open_settings_dialog)
        pdf_row.addWidget(self.edit_settings_button)

        pdf_layout.addLayout(pdf_row)

        layout.addWidget(pdf_frame)
        pdf_frame.setEnabled(False)

        # ~~~~~~~~~~~~~~~ csv frame ~~~~~~~~~~~~~~~#
        csv_frame = QFrame()
        csv_frame.setFrameShape(QFrame.StyledPanel)
        csv_layout = QVBoxLayout(csv_frame)

        csv_title_label = QLabel("Export CSV")
        csv_title_label.setStyleSheet("font-weight: bold;")
        csv_layout.addWidget(csv_title_label)

        csv_layout.addWidget(QLabel("Export tabulaire des entités intersectées pour chaque couche :"))

        self.export_csv_button = QPushButton("Exporter les CSV")
        self.export_csv_button.clicked.connect(self._on_export_csv)
        csv_layout.addWidget(self.export_csv_button)

        layout.addWidget(csv_frame)
        csv_frame.setEnabled(False)

        doc_label = QLabel()
        doc_label.setText(
            '<a href="https://github.com/ecolabdata/secateur" \
            style="color: blue;">Documentation du plugin</a>'
        )
        doc_label.setOpenExternalLinks(True)
        doc_label.setTextFormat(RichText)
        layout.addWidget(doc_label)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(RichText)
        self.status_label.setOpenExternalLinks(False)
        self.status_label.linkActivated.connect(self._on_status_link_clicked)
        layout.addWidget(self.status_label)

        layout.addStretch()
        self.setWidget(container)

        self.csv_frame = csv_frame
        self.pdf_frame = pdf_frame

        self.basemap_combo.basemapGroupCreated.connect(self._on_basemap_group_created)
        self.basemap_combo.currentIndexChanged.connect(self._on_basemap_selected)
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        has_results = bool(self._resolve_result_layers())

        self.csv_frame.setEnabled(has_results)
        self.pdf_frame.setEnabled(has_results)

    def _set_status(self, message: str | None, level: str = "info") -> None:
        if message:
            self.status_label.setText(message)

        color_map = {"info": "", "warning": "color: orange;", "error": "color: red;"}
        self.status_label.setStyleSheet(color_map.get(level, "") or "")

        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)

    def _resolve_selected_layer(self) -> QgsVectorLayer | None:
        if not self.state.selected_layer_id:
            return None

        return LayerResolver.get_vector(self.state.selected_layer_id)

    def _resolve_result_layers(self) -> list[QgsMapLayer]:
        return LayerResolver.get_many(self.state.result_layer_ids)

    def _resolve_basemap(self) -> QgsMapLayer | None:
        layer_id = self.basemap_combo.selected_layer_id()
        if not layer_id:
            return None
        return LayerResolver.get(layer_id)

    def _on_include_raster_changed(self, state: int) -> None:
        self.settings.include_raster = state == Qt.Checked

    def _open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self.settings, self.image_manager, self)

        try:
            if not dlg.exec_():
                return

            values = dlg.get_values()

            author = values["author"]
            if not author:
                self._set_status("Auteur invalide.", "error")
                return

            logo_path = self.settings.logo_path  # fallback

            if values["logo"]:
                logo_path = self.image_manager.safe_import_logo(values["logo"])

            self.settings.author = author
            self.settings.logo_path = logo_path

            self._set_status("Paramètres mis à jour.", "info")

        except ValueError as e:
            # erreurs métier (validation image)
            self._set_status(str(e), "error")

        except Exception as e:
            # erreurs inattendues (IO, filesystem, etc.)
            self._set_status(f"Erreur inattendue : {e}", "error")

    def _on_basemap_group_created(self) -> None:
        self._set_status(
            (
                f"Le groupe {BASEMAP_GROUP_NAME} a été créé en bas de l'arborescence des couches. "
                "Veuillez y ajouter les couches à utiliser comme fond de carte."
            ),
            "warning",
        )

    def _on_basemap_selected(self, _: int) -> None:
        layer_id = self.basemap_combo.selected_layer_id()

        if layer_id is None:
            self._set_status("Aucun fond de carte sélectionné.", "info")
            return

        layer = LayerResolver.get(layer_id)

        if layer is not None:
            self._set_status(
                f"Fond de carte sélectionné : {layer.name()}",
                "info",
            )

    # ──────────────────────────────────────────────
    #  Execution
    # ──────────────────────────────────────────────

    def _execute(self) -> None:
        # Use a context manager to guarantee cursor restoration
        # even if an exception occurs or the function returns early.

        selection = self.service.select(self.iface)

        if selection.message:
            self._set_status(selection.message, selection.level)

        if selection.layer is None:
            return

        self.state.selected_layer_id = selection.layer.id() if selection.layer else None

        try:
            with wait_cursor():
                self._run_process()
        except Exception as e:
            self._set_status(f"Erreur d'exécution : {e}", "error")
        finally:
            self.run_button.setEnabled(True)
            self._feedback = None

    def _run_process(self) -> ProcessResult:
        selected_layer = self._resolve_selected_layer()

        if selected_layer is None:
            self._set_status(
                "La couche sélectionnée n'existe plus.",
                "error",
            )

            return ProcessResult(
                [],
                "La couche sélectionnée n'existe plus.",
                "error",
            )

        feedback = self._create_feedback()

        result = self.service.run(
            selected_layer.id(),
            feedback,
        )

        self.state.result_layer_ids = result.result_layer_ids

        self._set_status(result.message, result.level)

        self._update_ui_state()

        self._finish_progress(result.message)
        return result

    def _on_export_csv(self) -> None:
        if not self._verify_results_exist():
            return

        folder = QFileDialog.getExistingDirectory(self, "Dossier CSV")
        if not folder:
            return

        self._begin_busy_ui("Export CSV en cours...")

        QTimer.singleShot(
            0,
            lambda: self._execute_csv_export(folder),
        )

    def _execute_csv_export(self, folder: str) -> None:
        feedback = self._create_feedback()

        try:
            with wait_cursor():
                result = export_results_to_csv(
                    self._resolve_result_layers(),
                    folder,
                    feedback=feedback,
                )

                self._set_status(
                    f'{len(result)} CSV exporté(s).<br><a href="{folder}">Ouvrir le dossier de sortie</a>',
                    "info",
                )

        except Exception as e:
            logger.exception(f"CSV export failed: {e}")

            self._set_status(
                f"Erreur lors de l'export CSV: {e}",
                "error",
            )

        finally:
            self._end_busy_ui()

    def _on_export_pdf(self) -> None:
        if not self._verify_results_exist():
            return

        folder = QFileDialog.getExistingDirectory(self, "Dossier PDF")
        if not folder:
            return

        title = self.title_input.text().strip()

        if not title:
            self._set_status("Le titre ne peut pas être vide.", "error")
            return

        self._begin_busy_ui("Export PDF en cours...")

        QTimer.singleShot(
            0,
            lambda: self._execute_pdf_export(folder, title),
        )

    def _execute_pdf_export(self, folder: str, title: str) -> None:
        feedback = self._create_feedback()
        try:
            with wait_cursor():
                # Generate multi-page PDF with same parameters
                multipdf_path = export_results_to_multi_page_pdf(
                    self._resolve_result_layers(),
                    folder,
                    self.settings.logo_path,
                    basemap_layer=self._resolve_basemap(),
                    author=self.settings.author,
                    title=title,
                    feedback=feedback,
                )

                legend_output_path = Path(folder)
                layer_names = [layer.name() for layer in self._resolve_result_layers()]
                legend_path = export_legend(
                    output_path=legend_output_path,
                    layer_names=layer_names,
                    logo_path=Path(self.settings.logo_path) if self.settings.logo_path else None,
                    title=title,
                    author=self.settings.author,
                )

                self.settings.pdf_title = title

                self._set_status(
                    f"PDF multi-page exporté : {multipdf_path}<br>"
                    f"Légende exportée : {legend_path}<br>"
                    f'<a href="{folder}">Ouvrir le dossier de sortie</a>',
                    "info",
                )

        except Exception as e:
            logger.exception(f"Direct PDF export failed: {e}")

            self._set_status(
                f"Erreur lors de l'export du PDF: {e}",
                "error",
            )

        finally:
            self._end_busy_ui()

    def _invalidate_results(self) -> None:
        self.state.result_layer_ids = []

        self._update_ui_state()

        self._set_status(
            ("Les couches de résultat ont été supprimées du projet. Relancez le traitement."),
            "warning",
        )

    def _verify_results_exist(self) -> bool:
        layers = self._resolve_result_layers()

        if not layers:
            self._invalidate_results()
            return False

        return True

    # Progress unchanged
    def _create_feedback(self) -> QgsProcessingFeedback:
        return QgsProcessingFeedback()

    def _finish_progress(self, text: str) -> None:
        self._set_status(text, "info")

    def _begin_busy_ui(self, message: str) -> None:
        self.run_button.setEnabled(False)
        self.export_pdf_button.setEnabled(False)
        self.export_csv_button.setEnabled(False)

        self._set_status(message, "info")

    def _end_busy_ui(self) -> None:
        self.run_button.setEnabled(True)
        self.export_pdf_button.setEnabled(bool(self._resolve_result_layers()))
        self.export_csv_button.setEnabled(bool(self._resolve_result_layers()))

        self._feedback = None

    def _on_status_link_clicked(self, path: str) -> None:
        """Open export folder."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

import os

from qgis.core import QgsSettings

from ..core.utils.path import get_icon_path


class SettingsManager:
    """Centralized management of the plugin's settings.

    - Single source of truth
    - Encapsulates QgsSettings
    - Typed, explicit API
    """

    BASE_KEY = "secateur"
    DEFAULT_LOGO = "logo.png"

    def __init__(self):
        self._settings = QgsSettings()

    # ~~~~~~~~~~~~~~~ raster ~~~~~~~~~~~~~~~#
    @property
    def include_raster(self) -> bool:
        raw = self._settings.value(
            f"{self.BASE_KEY}/include_raster",
            False,
        )
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1", "yes")

    @include_raster.setter
    def include_raster(self, value: bool) -> None:
        self._settings.setValue(
            f"{self.BASE_KEY}/include_raster",
            bool(value),
        )

    # ~~~~~~~~~~~~~~~ author ~~~~~~~~~~~~~~~#
    @property
    def author(self) -> str:
        return self._settings.value(f"{self.BASE_KEY}/author", "DDT")

    @author.setter
    def author(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("L'autheur ne peut pas être vide")
        self._settings.setValue(f"{self.BASE_KEY}/author", value.strip())

    # ~~~~~~~~~~~~~ pdf title ~~~~~~~~~~~~~~#
    @property
    def pdf_title(self) -> str:
        return self._settings.value(f"{self.BASE_KEY}/pdf_title", "Rapport")

    @pdf_title.setter
    def pdf_title(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Le titre ne peut pas être vide")
        self._settings.setValue(f"{self.BASE_KEY}/pdf_title", value.strip())

    # ~~~~~~~~~~~~~~~ logo ~~~~~~~~~~~~~~~~#
    @property
    def logo_path(self) -> str:
        path = self._settings.value(f"{self.BASE_KEY}/logo_path", "")
        if path:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Logo introuvable : {path}")
            return path

        default_path = get_icon_path(self.DEFAULT_LOGO)

        if not default_path or not os.path.exists(default_path):
            raise ValueError("Logo par défaut introuvable dans les ressources")

        return default_path

    @logo_path.setter
    def logo_path(self, value: str) -> None:
        if value and not os.path.exists(value):
            raise ValueError(f"Chemin logo invalide : {value}")

        self._settings.setValue(f"{self.BASE_KEY}/logo_path", value)

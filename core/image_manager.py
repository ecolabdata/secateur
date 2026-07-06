import os
import shutil

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QImage


class ImageManager:
    """Validate, resize, and store logo images used in PDF exports."""

    MAX_WIDTH = 2000
    MAX_HEIGHT = 2000

    TARGET_RATIO = 295 / 432
    RATIO_TOLERANCE = 0.15

    def validate_image(self, path: str) -> QImage:
        """Load and validate an image against the plugin's logo constraints.

        Args:
            path: Path to the image file to validate.

        Returns:
            The loaded ``QImage``.

        Raises:
            ValueError: If the image cannot be loaded, exceeds
                ``MAX_WIDTH``/``MAX_HEIGHT``, or its aspect ratio deviates
                from ``TARGET_RATIO`` by more than ``RATIO_TOLERANCE``.
        """
        img = QImage(path)

        if img.isNull():
            raise ValueError("Image invalide")

        if img.width() > self.MAX_WIDTH or img.height() > self.MAX_HEIGHT:
            raise ValueError("Image trop grande")

        ratio = img.width() / img.height()
        if abs(ratio - self.TARGET_RATIO) > self.RATIO_TOLERANCE:
            raise ValueError(f"Ratio image incorrect (attendu ~{self.TARGET_RATIO:.2f}, obtenu {ratio:.2f})")

        return img

    def normalize_image(self, path: str, output_path: str) -> str:
        """Validate, resize to the target logo dimensions, and save an image.

        Args:
            path: Path to the source image file.
            output_path: Path the resized image is written to.

        Returns:
            The *output_path* it was saved to.

        Raises:
            ValueError: If the source image fails ``validate_image`` checks.
        """
        img = self.validate_image(path)

        target_w, target_h = 295, 432

        resized = img.scaled(
            target_w,
            target_h,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        resized.save(output_path)
        return output_path

    @staticmethod
    def copy_to_local(path: str) -> str:
        """Copy an image into the plugin's local settings directory as ``logo.<ext>``.

        Args:
            path: Path to the source image file.

        Returns:
            Path of the copied file.
        """
        base_dir = QgsApplication.qgisSettingsDirPath()
        dest_dir = os.path.join(base_dir, "secateur")

        os.makedirs(dest_dir, exist_ok=True)

        _, ext = os.path.splitext(path)
        dest_path = os.path.join(dest_dir, f"logo{ext}")

        shutil.copyfile(path, dest_path)

        return dest_path

    def safe_import_logo(self, path: str) -> str:
        """Validate an image then copy it into the plugin's local settings directory.

        Args:
            path: Path to the source image file.

        Returns:
            Path of the copied logo file.

        Raises:
            ValueError: If the source image fails ``validate_image`` checks.
        """
        self.validate_image(path)
        return self.copy_to_local(path)

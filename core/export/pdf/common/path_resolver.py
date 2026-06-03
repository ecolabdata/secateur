"""
Common path resolution utilities for export configurations.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar("T")


def resolve_output_path(
    output_path: str | Path,
    filename_template: str,
    resource_base_path: Path,
) -> tuple[Path, Path]:
    """Resolve the output path for PDF exports.

    If *output_path* is a directory, a timestamped filename is created inside it.
    Otherwise *output_path* is returned unchanged.

    Args:
        output_path: The output path to resolve
        filename_template: Template for filename when output_path is a directory
        resource_base_path: Base path for resource files

    Returns:
        Tuple of (resolved_output_path, template_path)
    """
    from ....utils.formatting import timestamp_str

    # Resolve output path; if a directory is provided, create a timestamped filename
    output_path_obj = Path(output_path).expanduser()
    if output_path_obj.is_dir():
        timestamp = timestamp_str()
        output_path_obj = output_path_obj / filename_template.format(timestamp=timestamp)
    else:
        # Ensure parent directories exist
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Determine template path
    template_path = resource_base_path / "report_page.qpt"

    return output_path_obj, template_path


def resolve_legend_output_path(
    output_path: str | Path,
    filename_template: str,
    resource_base_path: Path,
) -> tuple[Path, Path]:
    """Resolve the output path for legend exports.

    If *output_path* is a directory, a timestamped filename is created inside it.
    Otherwise *output_path* is returned unchanged.

    Args:
        output_path: The output path to resolve
        filename_template: Template for filename when output_path is a directory
        resource_base_path: Base path for resource files

    Returns:
        Tuple of (resolved_output_path, template_path)
    """
    from ....utils.formatting import timestamp_str

    # Resolve output path; if a directory is provided, create a timestamped filename
    output_path_obj = Path(output_path).expanduser()
    if output_path_obj.is_dir():
        timestamp = timestamp_str()
        output_path_obj = output_path_obj / filename_template.format(timestamp=timestamp)
    else:
        # Ensure parent directories exist
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Determine template path
    template_path = resource_base_path / "legend_layout.qpt"

    return output_path_obj, template_path


def resolve_resource_base_path(current_file: str) -> Path:
    """Resolve the resource base path from the current file location.

    Args:
        current_file: __file__ of the calling module

    Returns:
        Path to the resources directory
    """
    return Path(current_file).resolve().parents[4] / "resources"

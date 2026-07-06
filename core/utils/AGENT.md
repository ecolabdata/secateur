# core/utils/ — shared utilities

## Purpose

Small, independent helper modules used across `core/` and `ui/`. Despite
the package name, this is not a single "utils blob" — each file owns one
concern (layer groups, visibility, resolving layers by ID, feedback
reporting, formatting, filesystem paths, rendering/symbology).

## Responsibilities

- **layers.py** — QGIS layer-tree group management (find/create/clear the
  results, created-objects, and basemap groups), layer discovery
  (`find_layers`, `iter_visible_layers`), and `iterate_layers` (a generic
  progress-reporting iteration helper used by CSV export).
- **layer_resolver.py** — `LayerResolver`, a tiny static-method utility to
  resolve `QgsMapLayer`/`QgsVectorLayer` instances by ID from the current
  project, tolerating missing/invalid IDs.
- **visibility.py** — toggle layer (and parent group) visibility;
  `set_layer_and_parents_visible` and `clear_all_visibility` are used by
  the PDF export pipeline to stage which layers are visible before
  rendering a layout.
- **feedback.py** — thin wrapper around `QgsProcessingFeedback` progress
  reporting (`update_feedback`) and per-layer performance reporting
  (`report_layer_metrics`).
- **formatting.py** — timestamp/date string formatting for filenames and
  PDF display text, QGIS attribute value formatting, filename
  sanitization.
- **path.py** — resource path helpers (`get_icon_path`) and a
  `resolve_output_path` (see pitfall below).
- **rendering.py** — renderer/symbol introspection (`is_simple_fill`,
  `set_layer_opacity`) used by the PDF export visibility styling step.

## Public API

Each file's public (non-underscore-prefixed) functions/classes are the
API; there is no package-level facade (`__init__.py` is empty). Import
directly from the submodule, e.g. `from core.utils.layers import find_group`.

## Dependencies

- `qgis.core` (layer tree, project, processing feedback).
- `core.constants` (group names), `core.logger`.
- `layer_resolver.py` → `layers.py`'s constants indirectly via
  `QgsProject`; `visibility.py` → `layers.py` (`find_tree_layer`).

## Modules that depend on this package

`core/intersection/*`, `core/export/*` (csv and pdf), and `ui/service.py`
all import from here directly.

## Invariants

- These modules must stay UI-free (no Qt widgets) and business-logic-free
  beyond their narrow concern — that's what keeps them independently
  reusable from both the intersection engine and the export pipeline.

## Common pitfalls

- **`path.py::resolve_output_path(output_path: str) -> tuple[str, str]`
  is dead code with zero callers anywhere in the repo.** It predates, and
  is unrelated to, the actively-used
  `core/export/pdf/common/path_resolver.py::resolve_output_path(...)`
  (different signature, `Path`-based, used by the PDF export config
  factory). The two are easy to confuse by name alone — check the import
  path, not just the function name, when searching for "the" output-path
  resolver.
- `feedback.py` importing from `core/intersection/intersection_metrics.py`
  is a known cross-package coupling (utils depending on the intersection
  engine); it's documented, not accidental, but be aware of it if you're
  trying to keep `utils/` independent of `intersection/`.

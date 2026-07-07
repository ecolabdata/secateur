# core/ — business logic layer

## Purpose

All QGIS-facing business logic that is not UI: layer/group management,
spatial intersection processing, and CSV/PDF export. Contains no Qt widget
code (dialogs, buttons, layouts are all in [ui/](../ui/AGENT.md)).

## Responsibilities

- Manage the plugin's QGIS layer-tree groups (results, created objects,
  basemap) and layer discovery/visibility — [utils/](utils/AGENT.md).
- Compute spatial intersections between a source layer and candidate
  layers — [intersection/](intersection/AGENT.md).
- Export intersection results to CSV and PDF (legend + multi-page report)
  — [export/](export/AGENT.md).
- Validate, resize, and store logo images used in PDF exports —
  [image_manager.py](image_manager.py).
- QGIS-native logging — [logger.py](logger.py) forwards Python `logging`
  calls to `QgsMessageLog` (visible in QGIS's Log Messages panel).
- Shared constants — [constants.py](constants.py) defines the (French,
  user-visible) QGIS layer-tree group names used throughout `core/` and
  `ui/`.

## Public API

Sub-packages export their own public API; see their AGENT.md files. At
this level, the only directly-imported symbols from outside `core/` are:
- `core.image_manager.ImageManager`
- `core.logger.logger`
- `core.constants.{RESULT_GROUP_NAME, CREATED_OBJECTS_GROUP_NAME, BASEMAP_GROUP_NAME}`
- `core.utils.layer_resolver.LayerResolver`
- everything re-exported by [core/export/__init__.py](export/AGENT.md)
- `core.intersection.intersection_context.build_intersection_context` /
  `filter_layers_by_extent`
- `core.intersection.intersection_processing.{prepare_layers, intersect_layers}`
- `core.intersection.intersection_results.add_results_to_project`

## Architectural constraints

- `core/` must stay UI-free. `ui/service.py` (`SecateurService`) is the
  only orchestrator allowed to call across `utils/`, `intersection/`, and
  `export/` in the same request; modules within `core/` should not need to
  know about each other's siblings unless already wired that way (see
  invariants below).
- Direct `QgsProject.instance()` access is allowed in `utils/layers.py`,
  `intersection_context.py`, `intersection_processing.py`, and the PDF
  services — this is a deliberate architectural trait of this plugin (no
  QGIS-runtime abstraction layer), not an oversight. See
  [docs/module_dependency_graph.md](../docs/module_dependency_graph.md).

## Invariants

- `constants.py` group names (`"Résultats secateur"`, `"Objet cible"`,
  `"Fond de carte"`) are French and **user-visible** in the QGIS layer
  tree — never translate or rename them; that would be a breaking change
  for users and for any saved QGIS project referencing these group names.
- `core/utils/feedback.py` depends on `core/intersection/intersection_metrics.py`
  — a known cross-cutting coupling between the export/feedback utilities
  and the intersection engine (see [docs/module_dependency_graph.md](../docs/module_dependency_graph.md)).

## Coding conventions specific to this module

- Docstrings, comments, and log messages (`logger.*`) are in English.
- `QgsProcessingFeedback.push*()` messages and any string that ends up
  displayed to the end user (via `ui/panel.py`'s `_set_status`, or baked
  into exported PDF/CSV content) stay in French. See
  [ui/AGENT.md](../ui/AGENT.md) for the full rule and examples.
- Google-style docstrings (`Args:`/`Returns:`/`Raises:`).

## Common pitfalls

- Don't assume an unused-looking function/parameter is dead code — this
  codebase is under active development and some apparently-unused pieces
  (e.g. `ImageManager.normalize_image`) are intentionally kept for planned
  features. Verify call sites across the *whole* repo before removing
  anything, and when in doubt, ask rather than delete.

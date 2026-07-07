# core/intersection/ — spatial intersection engine

## Purpose

Computes the spatial intersection between a user-selected reference
(source) layer and every eligible visible layer in the QGIS project, and
tracks per-layer performance metrics along the way.

## Responsibilities

- Build a reusable per-run execution context (source CRS/extent, a CRS
  transform cache, an extent cache) — `intersection_context.py`.
- Cheaply pre-filter candidate layers by bounding-box overlap before doing
  real intersection work — `may_intersect_source` /
  `filter_layers_by_extent` in `intersection_context.py`.
- Prepare layers for processing: create a spatial subset, reproject if
  needed, track per-layer timing — `intersection_processing.py`.
- Run the actual intersection via QGIS Processing algorithms
  (`native:extractbylocation`, with `native:fixgeometries` as a retry
  fallback, plus `native:reprojectlayer` / `gdal:warpreproject`) —
  `intersection_processing.py`.
- Apply the source layer's rendering/naming to result layers, and add
  results to the project under the results group —
  `intersection_results.py`.
- Track and format per-layer timing (bbox/reprojection/extraction
  seconds) — `intersection_metrics.py`.
- Generic "time this call" helper — `profiling.py::timed_call`.

## Public API

- `intersection_context.build_intersection_context(source_layer, *, include_raster=False)`
- `intersection_context.filter_layers_by_extent(context, layers)`
- `intersection_processing.prepare_layers(layers, context, feedback=None)`
- `intersection_processing.intersect_layers(source_layer, prepared_layers, context, feedback=None)`
- `intersection_results.add_results_to_project(result_layers)`
- `IntersectionExecutionContext`, `IntersectionMetrics`, `LayerMetrics`
  (dataclasses passed around by the above functions)

## Dependencies

- `qgis.core` (`QgsCoordinateTransform`, `QgsFeatureRequest`, ...) and
  `qgis.processing` (`processing.run(...)`, imported lazily inside
  functions to avoid a hard import-time dependency).
- `core.utils.feedback.report_layer_metrics`.

## Modules that depend on this package

`ui/service.py::SecateurService.run()` is the sole caller, orchestrating
`build_intersection_context` → `filter_layers_by_extent` →
`prepare_layers` → `intersect_layers` → `add_results_to_project`.

## Invariants

- `IntersectionExecutionContext` is built once per run and threaded
  through every step (`prepare_layers`, `intersect_layers`,
  `may_intersect_source`) — it is the single source of truth for the
  source CRS/extent and the CRS transform/extent caches. Don't bypass it
  by recomputing extents or transforms ad hoc.
- Every processing algorithm call (`processing.run(...)`) happens through
  the small `_extract_by_location`, `_fix_geometries`, `_reproject_layer`
  wrappers in `intersection_processing.py` — new algorithm calls should
  follow the same pattern (lazy `import processing`, explicit params
  dict) rather than importing `processing` at module scope.

## Coding conventions specific to this module

- Internal docstrings/comments in English; `feedback.pushWarning(...)`
  messages (e.g. the `extractbylocation` retry warning) stay in French —
  they are visible to the end user during processing. See
  [ui/AGENT.md](../../ui/AGENT.md) for the full French/English rule.

## Common pitfalls

- `_extract_by_location_with_retry` silently retries with
  `_fix_geometries` on **any** `Exception` from `native:extractbylocation`
  — this is intentional resilience against invalid geometries, not error
  masking to "fix" without understanding why it's there.
- `may_intersect_source` is a bounding-box test only (not a true geometry
  intersection test) — it exists purely to cheaply skip layers before the
  expensive `native:extractbylocation` call; don't rely on it for
  precision.

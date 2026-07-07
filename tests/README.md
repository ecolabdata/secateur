# Tests

Real tests against a QGIS installation (via `pytest-qgis`), not mocks —
see the main [README's Tests section](../README.md#tests) for environment
setup (`uv venv --system-site-packages`, then `uv run pytest`).

## Files

| File | Covers | Notes |
|---|---|---|
| `conftest.py` | Shared fixtures | `make_layer`: builds small in-memory `QgsVectorLayer`s from WKT. `_clean_qgis_project` (autouse): resets `QgsProject.instance()` before every test — without it, layers/groups added by one test leak into the next, since the project is a process-wide singleton. `_initialize_processing` (autouse, session): registers QGIS Processing providers (`native:*`, `gdal:*`), needed for `processing.run(...)` to work at all in a standalone test session. |
| `test_intersection.py` | `core/intersection/` | `IntersectionExecutionContext`, extent/CRS caching, bbox pre-filtering, and an end-to-end `prepare_layers` → `intersect_layers` run asserting the actual intersected feature comes out. |
| `test_service.py` | `ui/service.py::SecateurService` | `select()` (no active layer / non-vector / 0, 1, N features selected) and `run()` (unknown layer id, and a full intersection producing real result layers), via a `FakeIface` stand-in for QGIS's `iface`. |
| `test_utils.py` | `core/utils/` | `LayerResolver`, the layer-tree group helpers (`find_group`, `get_or_create_group`, the three named groups), `find_layers`/`iter_visible_layers`/`find_tree_layer`, `iterate_layers`, and `formatting.py`'s pure functions. |
| `test_export_csv.py` | `core/export/csv/export.py` | One CSV per vector layer, non-vector layers skipped, output directory auto-created. |
| `test_export_pdf.py` | `core/export/pdf/legend` + `multi_pdf` | **Smoke tests only**: asserts a non-empty PDF is produced end-to-end (template load → layout render → export). Does not inspect rendered content (would need page rasterization + reference-image comparison — out of scope so far). |
| `test_compat.py` | `compat.py` (Qt5/Qt6 shim) | Tests whichever branch the running QGIS actually uses; the other branch is `pytest.mark.skip`'d with a reason, not silently passed. On QGIS 3.34 (Qt5), the Qt6/QGIS4 branch shows up as `SKIPPED` — that's expected, not a failure, and can only be resolved by someone running this suite under a real QGIS4 install. |

## Known gaps

- **`ui/panel.py` and `ui/widgets/`** (button clicks, dialogs) are not
  covered — needs `qgis_bot`/simulated Qt events, deliberately deferred.
  Test manually in QGIS before merging changes there.
- PDF exports are smoke-tested (file exists, non-empty), not
  content-verified.

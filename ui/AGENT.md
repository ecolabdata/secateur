# ui/ — Qt UI layer

## Purpose

All Qt widget code: the dockable panel, its settings dialog, and the
small business-logic-free service layer that translates UI actions into
`core/` calls and QGIS side effects.

## Responsibilities

- **panel.py** — `SecateurPanel`, the `QDockWidget` shown/hidden from the
  plugin's toolbar action. Owns the panel's widgets, wires button clicks
  to `SecateurService`/`core.export` calls, and is the single place that
  reports status back to the user (`_set_status`).
- **service.py** — `SecateurService`, a UI-free orchestrator: `select()`
  validates/prepares the active QGIS selection, `run()` drives the
  intersection engine end-to-end (see
  [core/intersection/AGENT.md](../core/intersection/AGENT.md)). Returns
  explicit `SelectionResult`/`ProcessResult` value objects rather than
  raising or touching widgets directly.
- **settings.py** — `SettingsManager`, a typed wrapper around
  `QgsSettings` for the plugin's persisted preferences (author, PDF
  title, logo path, include-raster flag).
- **widgets/basemap_combo.py** — `BasemapComboBox`, a `QComboBox` that
  lists layers from the "Fond de carte" QGIS group, refreshed on popup.
- **widgets/settings_dialog.py** — `SettingsDialog`, the modal dialog for
  editing author/logo settings.

## Public API

- `ui.panel.SecateurPanel(iface, parent=None)` — constructed once by
  `Plugin._toggle_panel` (see root `AGENT.md`).
- `ui.service.SecateurService`, `SelectionResult`, `ProcessResult`.
- `ui.settings.SettingsManager`.

## Dependencies

- `core.export` (all three export functions), `core.image_manager.ImageManager`,
  `core.utils.layer_resolver.LayerResolver`, `core.constants`,
  `core.logger.logger`, `core.intersection.*` (via `SecateurService`).
- `compat.py` (root) for the Qt5/Qt6-differing enum aliases.

## Modules that depend on this package

None within the plugin — `ui/` is consumed only by `plugin.py`
(root), which is the top of the call graph.

## Architectural constraints

- `SecateurService` must stay Qt-free (no imports from `qgis.PyQt`) —
  it's the one place in the plugin designed to be testable without a Qt
  event loop (see `tests/test_service.py`).
- Only `panel.py` should call `_set_status`-style UI feedback; `service.py`
  communicates outcomes via return values (`SelectionResult`/`ProcessResult`),
  never by touching widgets.

## Invariants — the French/English language boundary

This plugin's audience is French-speaking QGIS users (French government
territorial-analysis workflow). The codebase intentionally mixes English
(code, internal docs) and French (user-visible content). When editing
anything here, the deciding question is **"does the end user see this
exact text?"**:

**Stays French (user-visible):**
- All widget text: button/label text, window titles, tooltips.
- Every string passed to `panel.py::_set_status(...)`, including
  `SelectionResult.message` / `ProcessResult.message` from `service.py`.
- `ValueError`/`FileNotFoundError` messages raised from
  `SettingsManager`'s setters/`logo_path` getter — they are caught in
  `panel.py` and re-displayed verbatim via `_set_status(str(e), "error")`.
- `QgsProcessingFeedback.pushInfo()`/`.pushWarning()` calls anywhere in
  `core/` — confirmed with the maintainer to be treated as user-visible
  (shown during processing), not as internal logging, even though they
  read like diagnostic messages.
- Anything baked into exported output: PDF title/author defaults, the
  `dd/mm/YYYY` date format, QGIS layer-tree group names
  (`core/constants.py`).

**Becomes/stays English (internal-only):**
- Docstrings, code comments, variable/function/class names.
- `logger.*` calls (`core/logger.py` forwards to QGIS's Log Messages
  panel — a developer/debug-facing panel most end users never open).

If you're unsure which bucket a given string falls into, trace where it
ends up (search for the variable holding it) before translating it either
way — get this wrong and you either leave the codebase inconsistently
documented or change what a real user sees.

## Common pitfalls

- Don't translate `feedback.push*()` message text to English even though
  nearby `logger.*` calls in the same file are in English — they follow
  different rules (see above).
- `ui/service.py::SecateurService`'s docstring says it contains "NO UI
  (Qt) dependency" — keep it that way; if you need a Qt type there,
  that's a sign the logic belongs in `panel.py` instead.

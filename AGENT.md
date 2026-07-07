# secateur — plugin root

## Purpose

QGIS 3.34+ plugin ("Sécateur") that performs spatial intersection between a
user-selected reference feature and every visible layer in the current
project, then lets the user export the results as CSV and/or a multi-page
PDF report with an accompanying legend. Built for French government
territorial-analysis workflows (ecolabdata / DDT).

## Responsibilities

This directory is the QGIS plugin bootstrap layer only. It does not contain
business logic — it wires the plugin into QGIS's plugin API and delegates
everything else to [core/](core/AGENT.md) and [ui/](ui/AGENT.md).

## Public API

- `classFactory(iface)` ([__init__.py](__init__.py)) — QGIS's mandatory
  plugin entry point. Called once by QGIS at load time.
- `Plugin` ([plugin.py](plugin.py)) — implements the `initGui()`/`unload()`
  lifecycle QGIS expects from a plugin object: adds the toolbar
  icon/menu entry, and creates/toggles the `SecateurPanel` dock widget
  (see [ui/AGENT.md](ui/AGENT.md)) lazily on first use.
- `compat.py` — Qt5/Qt6 compatibility aliases (see below).

## Important pitfalls

- **`compat.py` is load-bearing, not legacy.** It aliases the handful of Qt
  enum/attribute names that differ between Qt5 (QGIS 3.x) and Qt6
  (QGIS 4.x), e.g. `RichText`. It was added specifically to fix a crash on
  QGIS 4. Do not remove it or "clean it up" as dead compatibility code —
  add new aliases here as needed instead of hardcoding a Qt version.

## Coding conventions specific to this module

- User-facing strings (menu label, action text) are in French — this
  plugin's audience is French-speaking QGIS users. See
  [ui/AGENT.md](ui/AGENT.md) for the full French/English boundary that
  applies across the whole plugin.
- Root-level modules stay thin. Any behavior beyond "wire up QGIS and
  delegate" belongs in `core/` or `ui/`, not here.

## Dependencies

- `qgis.PyQt` (Qt bindings), `qgis.core`/`qgis.gui` via `iface`.
- `ui.panel.SecateurPanel`.

## Modules that depend on this

None — this is the top of the dependency graph; QGIS itself is the only
caller (via `classFactory`).

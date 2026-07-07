# core/export/ — export facade

## Purpose

Top-level facade re-exporting the three export entry points the rest of
the plugin uses: CSV export and the two PDF export flows. The actual PDF
architecture lives one level down in [pdf/](pdf/AGENT.md); this directory
itself only contains the facade and the small CSV exporter.

## Responsibilities

- Re-export a stable, flat public API regardless of how the PDF
  sub-packages are organized internally (`__init__.py`).
- CSV export: write one CSV file per result layer — `csv/export.py`.

## Public API

```python
from core.export import (
    export_results_to_csv,           # csv/export.py
    export_legend,                   # pdf/legend/__init__.py
    export_results_to_multi_page_pdf,  # pdf/multi_pdf/__init__.py
)
```

- `export_results_to_csv(result_layers, output_dir, feedback=None) -> list[str]`
  — writes one CSV per vector layer into `output_dir` (created if
  missing), returns the written file paths. Non-vector layers are
  skipped silently.

## Dependencies

- `csv/export.py` → `core.utils.formatting` (`_format_value`,
  `_safe_filename`), `core.utils.layers.iterate_layers`.
- `pdf/legend`, `pdf/multi_pdf` — see [pdf/AGENT.md](pdf/AGENT.md).

## Modules that depend on this package

`ui/panel.py` imports all three functions directly from `core.export`.

## Coding conventions specific to this module

- Keep `__init__.py` a pure re-export facade — don't add logic here; add
  it in `csv/export.py` or the relevant `pdf/` sub-package instead.

## Common pitfalls

- `export_results_to_csv` calls `QApplication.processEvents()` at the end
  to keep the UI responsive during large exports — this is a deliberate
  workaround for QGIS's single-threaded UI, not dead/leftover code.

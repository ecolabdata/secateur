# core/export/pdf/ — PDF export subsystem

## Purpose

Generates the plugin's two PDF outputs — a multi-page cartographic report
(`multi_pdf/`) and a paginated legend document (`legend/`) — from QGIS
print-layout templates (`.qpt` files). Both share a common infrastructure
in `common/` so neither reimplements layout loading, metadata rendering,
PDF export/merging, or layout-lifecycle cleanup.

## Responsibilities

- **common/** — everything reusable across both PDF flows:
  - `export/base_export_service.py::BasePdfExportService` — abstract
    template-method base: builds layouts via a `LayoutFactory`
    collaborator, exports each to a temp PDF via a `PdfExporter`
    collaborator, merges multi-page results via a `PdfMergerInterface`
    collaborator (or renames the single page if there's only one), then
    finalizes via an `ExportLifecycle` collaborator.
  - `export/collaborators.py` — the five collaborator interfaces above
    plus their `Default*` implementations (strategy pattern; see
    Architectural constraints).
  - `export/pdf_merger.py::PdfMerger` — thin wrapper around vendored
    `pypdf` to merge single-page PDFs.
  - `export/base_export_config_factory.py::ExportConfigFactory` —
    shared `default()` classmethod that resolves the output path/template
    path and normalizes the logo path; subclassed by
    `LegendExportConfig` and `MultiPagePdfExportConfig`.
  - `layout/base_layout.py::BasePdfLayout` — abstract base owning the
    underlying `QgsPrintLayout` and the `stabilize()` step; subclassed by
    `LegendLayout` and `MultiPdfLayout`.
  - `layout/metadata.py`, `layout/metadata_items.py` — render
    title/author/date/logo onto layout items shared by both flows
    (`MetadataRenderer`, `MetadataLayoutItems`, `get_metadata_layout_items`).
  - `layout/items.py` — generic, type-checked layout-item lookup
    (`get_required_item`/`get_optional_item`), used via PEP 695 generics.
  - `layout/visibility.py` — stage layer visibility for the export
    duration (`temporary_visible_layers` context manager).
  - `layout/extent.py` — compute a padded export extent from the source
    vector layer.
  - `lifecycle/cleanup.py`, `lifecycle/refresh.py` — deterministic Qt
    event processing + GC + layout item refresh sequence needed before/
    after rendering a layout (see Invariants — this is not optional
    boilerplate).
  - `template_loader.py::create_layout_from_template` — loads a `.qpt`
    file into a `QgsPrintLayout`.
  - `path_resolver.py` — resolves the final output path (timestamped if a
    directory was given) and the bundled template path.
  - `pdf_export.py::export_layout_to_pdf` — the actual
    `QgsLayoutExporter` call, plus output-path validation and a
    write-permission probe.
  - `models/` — `PdfExportOptions` (dpi, page size, vector/raster export
    flags) and `LayoutMetadata`/`LayoutMetadataFactory`.
- **legend/** — paginated legend PDF: `LegendExportService` builds one
  `LegendLayout` per page (via `LegendPaginator`/`LegendCostCalculator`,
  which estimate a "cost" per layer from its renderer to decide how many
  layers fit per page) and merges them.
- **multi_pdf/** — cartographic report PDF: `MultiPagePdfExportService`
  builds one overview page (source layer and basemap) plus one detail page per
  additional result layer (via `MultiPageLayoutFactory` /
  `MultiPagePageBuilder` / `MultiPdfLayout`) and merges them.

## Public API

- `pdf.legend.export_legend(*, output_path, layer_names, logo_path=None, max_legend_items_per_page=20, dpi=300, title="Légende", author="QGIS User") -> str`
- `pdf.multi_pdf.export_results_to_multi_page_pdf(result_layers, output_path, logo_path, basemap_layer=None, author="DDT", title="Résultats Secateur", feedback=None) -> str`

Both are re-exported from [core/export/__init__.py](../AGENT.md). Internal
consumers (subclasses, factories) use the `common/` building blocks
directly; treat everything in `common/` as an internal API shared
*between* `legend/` and `multi_pdf/`, not a public surface for `ui/`.

## Important classes

`BasePdfExportService`, `BasePdfLayout`, `ExportConfigFactory` (all
abstract template-method bases in `common/`), and their concrete pairs
`LegendExportService`/`MultiPagePdfExportService`,
`LegendLayout`/`MultiPdfLayout`, `LegendExportConfig`/`MultiPagePdfExportConfig`.

## Dependencies

- `qgis.core` (`QgsPrintLayout`, `QgsLayoutExporter`, `QgsLayoutItem*`).
- `vendor/pypdf` (via `PdfMerger`) — see root `AGENT.md`/README for why
  it's vendored rather than a pip dependency.
- `core.utils.formatting.display_date_str` for the metadata date text.
- `core.utils.feedback.update_feedback` for progress reporting.

## Modules that depend on this package

`core/export/__init__.py` (facade) and, transitively, `ui/panel.py`.

## Architectural constraints

- New PDF flows should be a `common/` base subclass (config, layout,
  service), following the `legend/`/`multi_pdf/` pattern, not a
  standalone implementation — that's the whole point of `common/`.
- `legend/` and `multi_pdf/` do not depend on each other. Keep it that
  way; shared behavior belongs in `common/`.

## Invariants

- **PyQt/SIP object lifetime.** Several places keep a Python reference to
  a QGIS/Qt object alive by attaching it as an arbitrary attribute on a
  longer-lived object, to prevent the SIP wrapper from being garbage
  collected while C++ still holds a pointer to it — e.g.
  `legend_tree.py::configure_legend` does
  `layout._secateur_legend_root = legend_root`. Do not "clean up" these
  assignments; removing them can reintroduce dangling-pointer crashes.
  `lifecycle/cleanup.py::finalize_export_cycle` and
  `lifecycle/refresh.py::stabilize_layout` exist for the same reason
  (deterministic `QApplication.processEvents()` + `gc.collect()` +
  refresh sequence) — always call them at the point in the export
  pipeline where they're already wired in; don't skip them for
  "simplification."
- `template_loader.py::create_layout_from_template` no longer removes an
  existing same-named layout before loading a new one (see the comment
  in that function) — this was deliberately changed after it caused
  dangling Python wrappers. Don't reintroduce that removal step.

## Coding conventions specific to this module

- Docstrings/comments in English (Google style). Metadata defaults that
  are visibly part of the PDF output (`title="Légende"`,
  `title="Résultats Secateur"`, the `f"Auteur: {metadata.author}"` label
  text in `layout/metadata.py`) stay in French — they are literally
  printed on the generated PDF.

## Common pitfalls

- `PdfExportOptions.page_size` is defined but not read anywhere in the
  export pipeline (page size is presumably driven by the `.qpt` template
  instead) — don't assume setting it changes the output. Kept as-is for
  now (planned future use), not removed.

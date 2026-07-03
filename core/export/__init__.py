"""Export package facade.

Provides convenient imports for CSV, legend and multi-page PDF export functions.
"""

from .csv.export import export_results_to_csv
from .pdf.legend import export_legend
from .pdf.multi_pdf import export_results_to_multi_page_pdf

__all__ = [
    "export_results_to_csv",
    "export_legend",
    "export_results_to_multi_page_pdf",
]

"""
academic-latex-ci: Continuous Integration, 2D Collision Detection, and
Multi-Surface Synchronization for Academic LaTeX Papers and Theses.
"""

from .core.overleaf import OverleafClient
from .core.gdocs import GDocExtractor
from .audits.layout import audit_pdf_layout, audit_vertical_collisions_on_page
from .audits.reconciliation import audit_reconciliation, audit_metadata_symmetry
from .audits.code_lint import audit_code_cleanliness

__version__ = "0.1.0"
__author__ = "Eneko Ruiz"

__all__ = [
    "OverleafClient",
    "GDocExtractor",
    "audit_pdf_layout",
    "audit_vertical_collisions_on_page",
    "audit_reconciliation",
    "audit_metadata_symmetry",
    "audit_code_cleanliness",
]

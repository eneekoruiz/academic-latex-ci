"""
Google Docs and Word (.docx) Extraction and Normalization.

Extracts paragraphs, headings, bullet lists, and tables from academic reports
exported from Google Drive / Google Docs for bidirectional reconciliation.
"""

from pathlib import Path
from typing import Dict, List, Optional

try:
    import docx
except ImportError:
    docx = None


class GDocExtractor:
    """Extracts clean text and metadata from Word / Google Docs documents."""

    def __init__(self, docx_path: Path):
        self.docx_path = Path(docx_path)
        if not self.docx_path.exists():
            raise FileNotFoundError(f"Document not found at: {docx_path}")

    def extract_paragraphs(self) -> List[str]:
        """Extracts non-empty paragraph text strings in document order."""
        if docx is None:
            raise ImportError("python-docx is required. Install with: pip install python-docx")

        doc = docx.Document(str(self.docx_path))
        paragraphs = []
        for p in doc.paragraphs:
            txt = p.text.strip()
            if txt:
                paragraphs.append(txt)
        return paragraphs

    def extract_metadata(self) -> Dict[str, Optional[str]]:
        """Extracts standard academic metadata (title, subtitle, authors, advisor)."""
        paras = self.extract_paragraphs()
        metadata = {
            "title": paras[0] if len(paras) > 0 else None,
            "subtitle": paras[1] if len(paras) > 1 else None,
            "raw_paragraphs_count": len(paras)
        }
        return metadata

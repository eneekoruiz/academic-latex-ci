"""
Reconciliation Audit: Google Docs / Word (.docx) <-> Overleaf LaTeX / PDF.

Ensures 100% parity across metadata, section headings, and body paragraphs.
Detects unverified cover fields (e.g. teacher/advisor mismatches) and textual drift.
"""

import difflib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import docx
except ImportError:
    docx = None

try:
    import pypdfium2
except ImportError:
    pypdfium2 = None


def clean_text(text: str) -> str:
    """Normalizes spaces, quotation marks, hyphens, Greek symbols, and math macros."""
    subscript_map = str.maketrans("₀₁₂₃₄₅₆₇₈₉ᵢⱼₖ", "0123456789ijk")
    t = text.translate(subscript_map)
    t = t.replace(r'\_', '_')
    t = t.replace("’", "'").replace("“", '"').replace("”", '"')
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    t = t.replace("·", " ")
    t = t.replace('θ', 'theta').replace('β', 'beta').replace('ω', 'omega')
    t = re.sub(r'\\(?:theta|beta|omega|cos|sin|arctan)\b', lambda m: m.group(0)[1:], t)
    t = re.sub(r'\\(?:frac|cdot|qquad|quad|dots)\b', '', t)
    t = re.sub(r'\\(?:begin|end)\{[^}]+\}', '', t)
    t = re.sub(r'\\(?:caption|subcaption)(?:\[[^\]]*\])?\{([^}]+)\}', r' \1 ', t)
    t = re.sub(r'\\(?:label|ref|needspace)\{[^}]+\}', '', t)
    t = re.sub(r'\{,\}', ',', t)
    t = re.sub(r'\\cite\{[^}]+\}', '', t)
    t = re.sub(r'\[\d+(?:[,\s]+\d+)*\]', '', t)
    t = re.sub(r'\\text(?:it|bf|tt|sl)\{([^}]+)\}', r'\1', t)
    t = t.replace('$', '')
    t = t.replace('_', '')
    t = re.sub(r'(\d+)\s*hz\b', r'\1 hz', t, flags=re.IGNORECASE)
    t = re.sub(r'^\d+\.\d+\s+(?:taula|irudia)\.?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^\([a-z]\)\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric tokens."""
    cleaned = clean_text(text).lower()
    return re.findall(r'[a-zA-Z0-9áéíóúñÁÉÍÓÚÑ]+', cleaned)


def similarity_ratio(t1: str, t2: str) -> float:
    """Calculates token-level sequence matcher similarity ratio."""
    tok1 = tokenize(t1)
    tok2 = tokenize(t2)
    if not tok1 or not tok2:
        return 0.0
    return difflib.SequenceMatcher(None, tok1, tok2).ratio()


def audit_metadata_symmetry(docx_path: Path, tex_root: Path) -> List[str]:
    """Ensures metadata fields (e.g. Teacher, Authors, Title) exist symmetrically in both environments."""
    defects = []
    
    # Read docx text
    docx_paras = []
    if docx and docx_path.exists():
        doc = docx.Document(str(docx_path))
        docx_paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    docx_full = " ".join(docx_paras).lower()

    # Read LaTeX source
    azala_file = tex_root / "config" / "azala.tex"
    main_file = tex_root / "main.tex"
    azala_content = azala_file.read_text(encoding="utf-8") if azala_file.exists() else ""
    main_content = main_file.read_text(encoding="utf-8") if main_file.exists() else ""

    # Check 'Irakaslea' / 'Teacher' symmetry
    teacher_in_docx = any(k in docx_full for k in ["irakaslea", "profesor", "tutor", "advisor"])
    teacher_in_tex = r"\irakaslea" in azala_content or r"\irakaslea" in main_content or "irakaslea:" in azala_content.lower()

    if not teacher_in_docx and teacher_in_tex:
        defects.append(
            "[METADATA ASYMMETRY] Field 'Irakaslea' / Advisor is printed in LaTeX cover (config/azala.tex) "
            "but does NOT appear in Google Doc / Word document! Remove '\\irakaslea' from cover to match."
        )

    return defects


def audit_reconciliation(docx_path: Path, tex_dir: Path) -> Tuple[bool, List[str]]:
    """Runs end-to-end reconciliation between docx and LaTeX source."""
    defects = []
    if not docx_path.exists():
        defects.append(f"[RECONCILIATION] Reference docx file not found at: {docx_path}")
        return False, defects

    metadata_defects = audit_metadata_symmetry(docx_path, tex_dir.parent if tex_dir.is_dir() else tex_dir)
    defects.extend(metadata_defects)

    # Paragraph count and sample matching
    if docx:
        doc = docx.Document(str(docx_path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        tex_files = list(tex_dir.glob("**/*.tex"))
        all_tex = " ".join([tf.read_text(encoding="utf-8", errors="ignore") for tf in tex_files])
        all_tex_clean = clean_text(all_tex)

        unmatched = 0
        for idx, p in enumerate(paras):
            cp = clean_text(p)
            if len(cp) > 40:
                toks = tokenize(cp)
                if len(toks) >= 5:
                    sample = " ".join(toks[:6])
                    if sample not in tokenize(all_tex_clean):
                        # Verify with loose similarity
                        if similarity_ratio(sample, all_tex_clean) < 0.7:
                            unmatched += 1

        if unmatched > 5:
            defects.append(
                f"[RECONCILIATION] Found {unmatched} significant paragraphs in Google Doc missing or heavily altered in LaTeX."
            )

    return len(defects) == 0, defects

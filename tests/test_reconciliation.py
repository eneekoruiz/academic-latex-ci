"""Unit tests for reconciliation and metadata symmetry audits."""

import tempfile
from pathlib import Path
from academic_latex_ci.audits.reconciliation import clean_text, tokenize, audit_metadata_symmetry


def test_clean_text_normalizations():
    raw = r"$\theta = \arctan(c_1)$ eta $v = v_0 / (1 + K_V |\omega|)$"
    cleaned = clean_text(raw)
    assert "theta" in cleaned
    assert "omega" in cleaned
    assert "$" not in cleaned


def test_metadata_symmetry_detects_unverified_teacher():
    import docx
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        azala = config_dir / "azala.tex"
        azala.write_text(r"{\large \textbf{Irakaslea:} Elena Lazkano\par}", encoding="utf-8")
        
        # Real minimal docx without teacher
        docx_dummy = tmp_path / "test.docx"
        doc = docx.Document()
        doc.add_paragraph("Paretari jarraitzea")
        doc.save(str(docx_dummy))
        
        defects = audit_metadata_symmetry(docx_dummy, tmp_path)
        assert len(defects) == 1
        assert "METADATA ASYMMETRY" in defects[0]

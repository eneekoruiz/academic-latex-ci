"""Unit tests for code cleanliness linter."""

import tempfile
from pathlib import Path
from academic_latex_ci.audits.code_lint import audit_code_cleanliness


def test_clean_code_passes():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        code_dir = tmp_path / "src"
        code_dir.mkdir()
        clean_file = code_dir / "controller.py"
        clean_file.write_text("def run():\n    error = 0.5\n    return error\n", encoding="utf-8")
        
        defects = audit_code_cleanliness(tmp_path)
        assert len(defects) == 0


def test_residual_placeholder_detected():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        code_dir = tmp_path / "src"
        code_dir.mkdir()
        dirty_file = code_dir / "robot.py"
        dirty_file.write_text("x = 1.0 # Fake value, needs to be defined\n", encoding="utf-8")
        
        defects = audit_code_cleanliness(tmp_path)
        assert len(defects) == 1
        assert "RESIDUAL PLACEHOLDER DETECTED" in defects[0]


def test_dummy_telemetry_float_detected():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        code_dir = tmp_path / "kodea"
        code_dir.mkdir()
        telemetry_file = code_dir / "telemetry.py"
        telemetry_file.write_text("self.data_angular_error.append(8.97)\n", encoding="utf-8")
        
        defects = audit_code_cleanliness(tmp_path)
        assert len(defects) == 1
        assert "DUMMY TELEMETRY FLOAT 8.97 DETECTED" in defects[0]

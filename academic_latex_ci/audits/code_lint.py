"""
Automated Code Cleanliness Linter.

Detects residual template placeholders, hardcoded fake values,
dummy telemetric constants, and incomplete TODO markers in academic codebases.
"""

import re
from pathlib import Path
from typing import List


def audit_code_cleanliness(root_dir: Path) -> List[str]:
    """Scans student code directories for residual placeholders, fake values, or unfinished TODOs."""
    defects = []
    root = Path(root_dir)
    target_names = ["kodea", "src", "code", "scripts", "wall_following", "ros2_ws"]
    code_dirs = [root / d for d in target_names if (root / d).exists()]
    
    # If no standard subfolder exists, scan root directly for .py files
    if not code_dirs:
        code_dirs = [root]

    for cd in code_dirs:
        for py_file in cd.rglob("*.py"):
            posix_path = py_file.as_posix()
            # Skip initial teacher templates or virtual environments
            if any(skip in posix_path for skip in ["hasierakoa", "template", ".venv", "venv", "__pycache__", "site-packages"]):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                lower = line.lower()
                # 1. Residual placeholders
                if any(w in lower for w in ["fake value", "todo:", "## todo", "needs to be defined", "replace by calculated"]):
                    defects.append(
                        f"[CODE LINT] {py_file.name}:{idx}: RESIDUAL PLACEHOLDER DETECTED: '{line.strip()[:60]}'. "
                        f"Replace placeholder with real implementation before delivery."
                    )
                # 2. Hardcoded dummy telemetry constants (e.g. 8.97)
                if re.search(r'\.append\(\s*8\.97\s*\)', line):
                    defects.append(
                        f"[CODE LINT] {py_file.name}:{idx}: DUMMY TELEMETRY FLOAT 8.97 DETECTED! "
                        f"Replace hardcoded placeholder with real error variable (e.g. self.data_angular_error.append(error))."
                    )
    return defects

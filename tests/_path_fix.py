"""
Path bootstrap helper — adds the project root to sys.path.

Import this at the top of any test file to make direct execution work:
    import tests._path_fix  # noqa: F401

When running via pytest (python -m pytest), pytest.ini already sets
pythonpath=. so this is a no-op. It is only needed for VS Code's
"Run Python File" button which executes the file directly.
"""
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

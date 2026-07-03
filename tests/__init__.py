"""
Tests package bootstrap.

When a test file is run DIRECTLY with `python tests/test_foo.py`, Python's
sys.path starts at the tests/ directory.  This __init__.py adds the project
root (one level up from here) to sys.path so that all top-level package
imports (agents, database, mcp_servers, etc.) resolve correctly.

When tests are run with `pytest` or `python -m pytest`, pytest.ini already
sets pythonpath=. so this block is a no-op (the path is already there).
"""
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

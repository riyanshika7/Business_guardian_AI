# CHANGELOG — Business Guardian AI Repair

This log details the fixes and improvements applied to the Business Guardian AI codebase to ensure it is production-ready, compatible with Python 3.14, and compliant with all project constraints.

---

## 🛠️ Summary of Changes

### 1. Google ADK 1.4.2 Compatibility & State Propagation
*   **Centralized Runtime Patches:** Appended a one-time runtime patcher to [`config.py`](file:///c:/Users/riyan/Downloads/buisness%20guiardian%20AI%282%29/buisness%20guiardian%20AI/config.py). Because `config.py` is imported first by `main.py`, these patches execute on startup in both production (uvicorn) and testing environments.
*   **`ctx.state` Proxying:** Patched `InvocationContext`'s `__getattribute__` and `__setattr__` to transparently route `ctx.state` access to `ctx.session.state`, satisfying ADK 2.x code semantics.
*   **Deepcopy Storage Loss Resolution:** Patched `InMemorySessionService._create_session_impl` and `_get_session_impl` to share the same state dict reference as the stored session, preventing state updates from being discarded on deep-copying.
*   **Awaitable Session Wrappers:** Wrapped synchronous session methods in async coroutines to align with awaited calls in the workflow orchestrator.

### 2. Resilience and Timeout Handling (Fail-Fast MCP Integration)
*   **Fetch Timeout Limits:** Wrapped GWS Drive, GWS Calendar, and Search MCP client stdio calls in [`mcp_servers/sheets_mcp.py`](file:///c:/Users/riyan/Downloads/buisness%20guiardian%20AI%20(2)/buisness%20guiardian%20AI/mcp_servers/sheets_mcp.py), [`mcp_servers/calendar_mcp.py`](file:///c:/Users/riyan/Downloads/buisness%20guiardian%20AI%20(2)/buisness%20guiardian%20AI/mcp_servers/calendar_mcp.py), and [`mcp_servers/news_mcp.py`](file:///c:/Users/riyan/Downloads/buisness%20guiardian%20AI%20(2)/buisness%20guiardian%20AI/mcp_servers/news_mcp.py) with `asyncio.wait_for(..., timeout=3.0)`.
*   **Automatic Local Fallbacks:** If Node, npm, or credentials are missing/unauthenticated, the connection attempt fails fast and automatically falls back to reading local mock databases (CSVs) instead of hanging the entire uvicorn server loop.

### 3. Module Resolution & VS Code Integration
*   **Inline Path Bootstraps:** Prepend a path resolution block to all 8 agent scripts and 9 test files right below `from __future__ import annotations`:
    ```python
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
    ```
    This registers the project root on `sys.path` when running scripts directly via terminal or VS Code run buttons.
*   **Testing Configuration:** Created [`pytest.ini`](file:///c:/Users/riyan/Downloads/buisness%20guiardian%20AI%20(2)/buisness%20guiardian%20AI/pytest.ini) to set `pythonpath = .` and configured `.vscode/settings.json` to run tests via `pytest` by default.

### 4. Dependency & Import Fixes
*   **Conditional Imports:** Modified [`reports.py`](file:///c:/Users/riyan/Downloads/buisness%20guiardian%20AI%20(2)/buisness%20guiardian%20AI/reports.py) to wrap the `streamlit` import in a `try/except` block, preventing startup failures when Streamlit is not installed.
*   **MCP import fixes:** Cleaned up direct imports in `mcp_servers/risk_registry_mcp.py` to use standard import declarations rather than obsolete naming-conflict client helpers.

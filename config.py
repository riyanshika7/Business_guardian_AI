"""Centralized configuration module for Business Guardian AI.

Loads all environment variables from a .env file via python-dotenv.
Every secret, path, and tunable constant is defined here.
No other module in the project should call os.getenv() directly.

Reference documents:
    - PROJECT_CONSTITUTION.md §6 (Coding Standards)
    - ORCHESTRATOR_CONTRACT.md §3.4 (Configuration Settings)
    - ORCHESTRATOR_CONTRACT.md §3.5 (Guardrail Policies)
    - API_CONTRACTS.md §Security Requirements
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root (same directory as this file).
# override=False ensures real environment variables take precedence.
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

# ===================================================================
# 1. DATABASE
# ===================================================================
# SQLite database file path. Defaults to a file in the project root.
# Constitution §5: SQLite is the only permitted database engine in V1.
DB_PATH: str = os.getenv("DB_PATH", str(PROJECT_ROOT / "business_guardian.db"))

# ===================================================================
# 2. GOOGLE SHEETS MCP
# ===================================================================
# API_CONTRACTS §1 — Google Sheets document ID.
# Must be loaded from environment; never hard-coded.
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")

# ===================================================================
# 3. CALENDAR MCP
# ===================================================================
# API_CONTRACTS §2 — Corporate calendar identifier.
CALENDAR_ID: str = os.getenv("CALENDAR_ID", "")

# ===================================================================
# 4. NEWS MCP
# ===================================================================
# API_CONTRACTS §3 — Controls for the news aggregation feed.
# max_articles_per_topic must be 1–25; max_age_days must be 1–90.
NEWS_MAX_ARTICLES: int = int(os.getenv("NEWS_MAX_ARTICLES", "5"))
NEWS_MAX_AGE_DAYS: int = int(os.getenv("NEWS_MAX_AGE_DAYS", "30"))

# ===================================================================
# 5. RISK REGISTRY MCP
# ===================================================================
# API_CONTRACTS §5 — Look-back window for historical risk scores.
# history_days must be 1–365; defaults to 90.
RISK_HISTORY_DAYS: int = int(os.getenv("RISK_HISTORY_DAYS", "90"))

# ===================================================================
# 6. AGENT EXECUTION
# ===================================================================
# ORCHESTRATOR_CONTRACT §8.4 / §8.5 — Timeout and retry policy.
AGENT_TIMEOUT_SECONDS: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))
MAX_AGENT_RETRIES: int = int(os.getenv("MAX_AGENT_RETRIES", "2"))
PIPELINE_TIMEOUT_SECONDS: int = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "120"))
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "1800"))
# ===================================================================
# 7. GUARDRAILS
# ===================================================================
# ORCHESTRATOR_CONTRACT §9.3 — Confidence scores below this threshold
# trigger human_review_required status. Constitution §3 principle 4.
CONFIDENCE_THRESHOLD: int = int(os.getenv("CONFIDENCE_THRESHOLD", "60"))

# Default critical risk threshold (above which domains are categorized as critical).
CRITICAL_RISK_THRESHOLD: int = int(os.getenv("CRITICAL_RISK_THRESHOLD", "70"))

# ===================================================================
# 8. ANALYSIS SETTINGS
# ===================================================================
# Default look-ahead window (in days) for compliance and inventory
# analysis when the user request does not specify a value.
ANALYSIS_WINDOW_DAYS: int = int(os.getenv("ANALYSIS_WINDOW_DAYS", "30"))

# Default financial analysis period (in days).
DEFAULT_PERIOD_DAYS: int = int(os.getenv("DEFAULT_PERIOD_DAYS", "30"))

# ===================================================================
# 9. GEMINI API
# ===================================================================
# Used by the Communication Agent for LLM-powered report generation.
# Constitution §6: All secrets loaded from .env via config.py.
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
API_SECURITY_KEY: str = os.getenv("API_SECURITY_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ===================================================================
# 10. BUSINESS RULES
# ===================================================================
# Permitted business_type values accepted by the Orchestrator.
# ORCHESTRATOR_CONTRACT §3.1 — user request validation.
VALID_BUSINESS_TYPES: list[str] = ["retail", "agriculture", "ecommerce"]

# Permitted communication_type values for the Communication Agent.
# AGENT_CONTRACTS §7 — Communication Agent input validation.
VALID_COMMUNICATION_TYPES: list[str] = ["report", "email", "both"]

# Permitted score_type values stored in risk_scores table.
# DATA_MODELS §7 — RiskScore schema.
VALID_SCORE_TYPES: list[str] = [
    "inventory_risk",
    "finance_risk",
    "supplier_risk",
    "compliance_risk",
    "business_risk",
    "business_health",
    "confidence",
]

# Permitted event_type values for compliance events.
# DATA_MODELS §6 — ComplianceEvent schema.
VALID_COMPLIANCE_EVENT_TYPES: list[str] = [
    "tax",
    "license",
    "insurance",
    "regulatory",
    "contract_renewal",
    "other",
]

# Hardcoded domain weights for overall business risk scoring
RISK_WEIGHTS_BY_SECTOR = {
    "retail": {
        "inventory": 0.30,
        "finance": 0.30,
        "supplier": 0.20,
        "compliance": 0.20,
    },
    "agriculture": {
        "inventory": 0.40,
        "finance": 0.20,
        "supplier": 0.15,
        "compliance": 0.25,
    },
    "ecommerce": {
        "inventory": 0.25,
        "finance": 0.35,
        "supplier": 0.20,
        "compliance": 0.20,
    },
}

# General logging level
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# ===========================================================================
# ADK 1.4.2 Runtime Compatibility Patches
# ===========================================================================
# Applied at startup (config.py import time) so production uvicorn/main.py
# and test suites both run correctly under google-adk 1.4.2.
# ===========================================================================

def _apply_adk_runtime_patches():
    """Apply Google ADK compatibility overrides for version 1.4.2."""
    try:
        from google.adk.agents.invocation_context import InvocationContext
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        import inspect

        # -------------------------------------------------------------
        # Patch 1: Make ctx.state transparently proxy to ctx.session.state
        # -------------------------------------------------------------
        _orig_getattr = InvocationContext.__getattribute__
        _orig_setattr = InvocationContext.__setattr__

        def _ctx_getattribute(self, name):
            if name == 'state':
                try:
                    session = _orig_getattr(self, 'session')
                    return session.state
                except AttributeError:
                    raise AttributeError(
                        "'InvocationContext' has no attribute 'state': session not initialized"
                    )
            return _orig_getattr(self, name)

        def _ctx_setattr(self, name, value):
            if name == 'state':
                try:
                    session = _orig_getattr(self, 'session')
                    if value is not session.state and isinstance(value, dict):
                        session.state.update(value)
                except AttributeError:
                    pass
                return
            _orig_setattr(self, name, value)

        InvocationContext.__getattribute__ = _ctx_getattribute
        InvocationContext.__setattr__ = _ctx_setattr

        # -------------------------------------------------------------
        # Patch 2: Fix session.state.update() deepcopy state loss in ADK 1.4.2
        # -------------------------------------------------------------
        _orig_create_impl = InMemorySessionService._create_session_impl
        _orig_get_impl = InMemorySessionService._get_session_impl

        def _share_stored_state(session_service, copied_session, app_name, user_id):
            stored = (
                session_service.sessions
                .get(app_name, {})
                .get(user_id, {})
                .get(copied_session.id)
            )
            if stored is not None:
                object.__setattr__(copied_session, 'state', stored.state)

        def _patched_create_impl(self, *, app_name, user_id, state=None, session_id=None):
            copied_session = _orig_create_impl(
                self, app_name=app_name, user_id=user_id,
                state=state, session_id=session_id,
            )
            _share_stored_state(self, copied_session, app_name, user_id)
            return copied_session

        def _patched_get_impl(self, *, app_name, user_id, session_id, config=None):
            copied_session = _orig_get_impl(
                self, app_name=app_name, user_id=user_id,
                session_id=session_id, config=config,
            )
            if copied_session is not None:
                _share_stored_state(self, copied_session, app_name, user_id)
            return copied_session

        InMemorySessionService._create_session_impl = _patched_create_impl
        InMemorySessionService._get_session_impl = _patched_get_impl

        # -------------------------------------------------------------
        # Patch 3: Awaitable session methods wrapping (in case of ADK < 1.x)
        # -------------------------------------------------------------
        original_create = InMemorySessionService.create_session
        original_append = InMemorySessionService.append_event

        if not inspect.iscoroutinefunction(original_create):
            async def async_create_session(self, *, app_name, user_id, state=None, session_id=None):
                return original_create(self, app_name=app_name, user_id=user_id,
                                       state=state, session_id=session_id)
            InMemorySessionService.create_session = async_create_session

        if not inspect.iscoroutinefunction(original_append):
            async def async_append_event(self, session, event):
                return original_append(self, session, event)
            InMemorySessionService.append_event = async_append_event

    except Exception:
        pass


_apply_adk_runtime_patches()

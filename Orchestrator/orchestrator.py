"""Orchestrator — central coordinator for the Business Guardian AI pipeline.

Receives analysis requests, manages shared state, delegates to workflow.py
for MCP/agent execution, enforces guardrails, handles HITL pause/resume,
and assembles the dashboard payload.

Integration points
------------------
* ``workflow.py``      — MCP data gathering + agent dispatch (dict-based state)
* ``state_manager.py`` — Pydantic SharedState model & sub-models
* ``config.py``        — environment configuration constants
* ``main.py``          — FastAPI endpoints call ``start_analysis`` / ``approve_analysis``

Reference documents
-------------------
* ORCHESTRATOR_CONTRACT.md  §1–§15  (full orchestrator specification)
* AGENT_CONTRACTS.md        §1–§8   (agent I/O schemas)
* API_CONTRACTS.md          §1–§5   (MCP I/O schemas)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from config import (
    CONFIDENCE_THRESHOLD,
    VALID_BUSINESS_TYPES,
    VALID_COMMUNICATION_TYPES,
    CACHE_TTL_SECONDS,
)
from guardrails.audit_logger import log_event
from Orchestrator.state_manager import PipelineStatus
from Orchestrator import workflow

logger = logging.getLogger(__name__)

# ===================================================================
# In-memory cache for active runs (keyed by run_id)
# ORCHESTRATOR_CONTRACT §2.3 — Shared State Caching
# ===================================================================
_active_runs: dict[str, dict[str, Any]] = {}

def _prune_expired_runs() -> None:
    """Evict runs from _active_runs cache that are older than CACHE_TTL_SECONDS."""
    now = datetime.now(timezone.utc)
    expired_run_ids = []
    
    for r_id, run_state in list(_active_runs.items()):
        started_at_str = run_state.get("started_at")
        if started_at_str:
            try:
                # Strptime parses Z format as UTC
                started_at = datetime.strptime(started_at_str.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                age = (now - started_at).total_seconds()
                if age > CACHE_TTL_SECONDS:
                    expired_run_ids.append(r_id)
            except Exception as ex:
                logger.error(f"Error parsing started_at for run {r_id}: {ex}")
                
    for r_id in expired_run_ids:
        _active_runs.pop(r_id, None)
        logger.info("Evicted expired run from cache: run_id=%s", r_id)


# ===================================================================
# Orchestrator public API
# ===================================================================

async def start_analysis(inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute Phase 1 of the analysis pipeline.

    Called by ``POST /analyze``.  Validates the user request, runs the
    MCP layer, dispatches all agents through the Communication Agent,
    then pauses at the HITL gate and returns an intermediate dashboard
    payload.

    ORCHESTRATOR_CONTRACT §6.2 — Steps 1–16.

    Parameters
    ----------
    inputs:
        Validated user request body matching §3.1 schema.

    Returns
    -------
    dict
        Dashboard payload (intermediate — ``system_status`` will be
        ``"awaiting_human_approval"`` on success).
    """
    # Prune expired runs from volatile memory cache
    _prune_expired_runs()

    # ------------------------------------------------------------------
    # Step 1: Validate user request
    # ------------------------------------------------------------------
    validation_error = _validate_request(inputs)
    if validation_error is not None:
        return validation_error

    # ------------------------------------------------------------------
    # Steps 2–4: Create state, generate run_id, log pipeline_start
    # ------------------------------------------------------------------
    state = _create_initial_state(inputs)
    run_id: str = state["run_id"]
    logger.info("Pipeline started — run_id=%s business_id=%s", run_id, state["business_id"])
    log_event(run_id, "pipeline_start", status="success")

    try:
        # --------------------------------------------------------------
        # Steps 5–10: MCP Layer
        # --------------------------------------------------------------
        await workflow.execute_mcp_layer(state)

        # --------------------------------------------------------------
        # Steps 11–16: Parallel agents → Risk Tracker → Strategy →
        #              Communication → HITL pause
        # --------------------------------------------------------------
        await workflow.execute_pipeline_phase_1(state)

    except RuntimeError as exc:
        # Workflow raises RuntimeError on critical MCP / agent failures.
        logger.error("Pipeline halted — run_id=%s error=%s", run_id, exc)
        state["system_status"] = "error"
        log_event(run_id, "pipeline_error", error_code="PIPELINE_HALTED", status="error")
        return _get_dashboard_payload(state)

    except Exception as exc:
        # Catch-all for unexpected errors (§10.4).
        logger.exception("Unexpected error — run_id=%s", run_id)
        state["system_status"] = "error"
        state["errors"].append({
            "error_code": "UNEXPECTED_ERROR",
            "error_message": str(exc),
            "source": "orchestrator",
        })
        log_event(run_id, "pipeline_error", error_code="UNEXPECTED_ERROR", status="error")
        return _get_dashboard_payload(state)

    # ------------------------------------------------------------------
    # Step 16: Cache state for HITL pause
    # ------------------------------------------------------------------
    _active_runs[run_id] = state
    logger.info("HITL pause — run_id=%s cached for approval", run_id)

    return _get_dashboard_payload(state)


async def approve_analysis(run_id: str, approved: bool) -> dict[str, Any]:
    """Execute Phase 2 of the analysis pipeline after HITL decision.

    Called by ``POST /analyze/approve``.  Retrieves cached shared state,
    dispatches the Evaluation Agent on approval, persists results, and
    returns the final dashboard payload.

    ORCHESTRATOR_CONTRACT §6.2 — Steps 17–21.

    Parameters
    ----------
    run_id:
        UUID of the paused analysis run.
    approved:
        ``True`` if the human approved the communication draft.

    Returns
    -------
    dict
        Final dashboard payload.
    """
    # ------------------------------------------------------------------
    # Step 17: Retrieve cached state
    # ------------------------------------------------------------------
    state = _active_runs.get(run_id)
    if state is None:
        logger.warning("Approval failed — run_id=%s not found in active runs", run_id)
        return _error_payload(
            run_id=run_id,
            error_code="RUN_NOT_FOUND",
            error_message=f"No active run found for run_id '{run_id}'. "
                          "The run may have expired or already been completed.",
        )

    try:
        # --------------------------------------------------------------
        # Steps 17–20: Phase 2 execution (Evaluation + DB persistence)
        # --------------------------------------------------------------
        await workflow.execute_pipeline_phase_2(state, approved)

    except RuntimeError as exc:
        logger.error("Phase 2 halted — run_id=%s error=%s", run_id, exc)
        state["system_status"] = "error"
        log_event(run_id, "pipeline_error", error_code="PHASE2_HALTED", status="error")

    except Exception as exc:
        logger.exception("Unexpected error in Phase 2 — run_id=%s", run_id)
        state["system_status"] = "error"
        state["errors"].append({
            "error_code": "UNEXPECTED_ERROR",
            "error_message": str(exc),
            "source": "orchestrator",
        })
        log_event(run_id, "pipeline_error", error_code="UNEXPECTED_ERROR", status="error")

    # ------------------------------------------------------------------
    # Apply confidence threshold guardrail (§9.3)
    # ------------------------------------------------------------------
    eval_report = state.get("agent_reports", {}).get("evaluation_report")
    if eval_report and state["system_status"] not in ("error",):
        confidence = eval_report.get("confidence_score", 100)
        if confidence < CONFIDENCE_THRESHOLD:
            state["system_status"] = "human_review_required"
            log_event(run_id, "guardrail_confidence_flagged", status="success")

    # ------------------------------------------------------------------
    # Step 21: Remove from cache and return final payload
    # ------------------------------------------------------------------
    _active_runs.pop(run_id, None)

    completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["completed_at"] = completed_at
    log_event(run_id, "pipeline_complete", status=state.get("system_status", "success"))
    logger.info("Pipeline complete — run_id=%s status=%s", run_id, state.get("system_status"))

    return _get_dashboard_payload(state)


# ===================================================================
# Internal helpers
# ===================================================================

def _validate_request(inputs: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the user request per ORCHESTRATOR_CONTRACT §3.1.

    Returns a structured error payload on failure, or ``None`` on success.
    """
    required_fields = [
        "business_id", "business_name", "business_type",
        "period_days", "analysis_window_days",
    ]

    for field in required_fields:
        value = inputs.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return _error_payload(
                error_code="VALIDATION_ERROR",
                error_message=f"Required field '{field}' is missing or empty.",
            )

    business_type = inputs.get("business_type", "")
    if business_type not in VALID_BUSINESS_TYPES:
        return _error_payload(
            error_code="VALIDATION_ERROR",
            error_message=f"business_type '{business_type}' is invalid. "
                          f"Permitted values: {VALID_BUSINESS_TYPES}",
        )

    comm_type = inputs.get("communication_type", "both")
    if comm_type not in VALID_COMMUNICATION_TYPES:
        return _error_payload(
            error_code="VALIDATION_ERROR",
            error_message=f"communication_type '{comm_type}' is invalid. "
                          f"Permitted values: {VALID_COMMUNICATION_TYPES}",
        )

    period_days = inputs.get("period_days", 0)
    if not isinstance(period_days, int) or period_days <= 0:
        return _error_payload(
            error_code="VALIDATION_ERROR",
            error_message="period_days must be a positive integer.",
        )

    window_days = inputs.get("analysis_window_days", 0)
    if not isinstance(window_days, int) or window_days <= 0:
        return _error_payload(
            error_code="VALIDATION_ERROR",
            error_message="analysis_window_days must be a positive integer.",
        )

    return None


def _create_initial_state(inputs: dict[str, Any]) -> dict[str, Any]:
    """Build the initial shared state dict from validated user inputs.

    The dict structure mirrors ``SharedState`` from ``state_manager.py``
    but uses plain dicts for direct compatibility with ``workflow.py``.

    ORCHESTRATOR_CONTRACT §5.
    """
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        # Run identity & user request
        "run_id": run_id,
        "business_id": inputs["business_id"],
        "business_name": inputs["business_name"],
        "business_type": inputs["business_type"],
        "period_days": inputs.get("period_days", 30),
        "analysis_window_days": inputs.get("analysis_window_days", 30),
        "communication_type": inputs.get("communication_type", "both"),
        "recipient_name": inputs.get("recipient_name"),

        # MCP data container
        "mcp_data": {
            "inventory_data": [],
            "sales_data": [],
            "expenses_data": [],
            "supplier_data": [],
            "compliance_data": [],
            "supplier_intelligence": [],
            "supplier_news": [],
            "industry_news": [],
            "supplier_profiles": [],
            "supplier_risk_data": [],
            "risk_history": [],
            "risk_status": {},
            "risk_trends": [],
            "google_sheets_mcp_status": "pending",
            "calendar_mcp_status": "pending",
            "news_mcp_status": "pending",
            "supplier_intelligence_mcp_status": "pending",
            "risk_registry_mcp_status": "pending",
        },

        # Agent reports
        "agent_reports": {
            "inventory_risk_report": None,
            "finance_risk_report": None,
            "supplier_risk_report": None,
            "compliance_risk_report": None,
            "business_risk_report": None,
            "strategy_report": None,
            "communication_draft": None,
            "evaluation_report": None,
        },

        # Guardrail state
        "guardrail_state": {
            "human_approval_required": True,
            "human_approval_status": "pending",
            "confidence_threshold_passed": None,
            "validation_passed": None,
        },

        # Pipeline status & metadata
        "system_status": "running",
        "started_at": now,
        "completed_at": None,
        "errors": [],

        # Products buffer (populated by workflow.execute_mcp_layer)
        "products": [],
    }


def _get_dashboard_payload(state: dict[str, Any]) -> dict[str, Any]:
    """Assemble the dashboard response from shared state.

    Matches ORCHESTRATOR_CONTRACT §12.1 — Dashboard Payload Schema.

    Called both at HITL pause (intermediate) and after pipeline
    completion (final).
    """
    agent_reports = state.get("agent_reports", {})

    # --- Extract scores -----------------------------------------------
    biz_risk = agent_reports.get("business_risk_report") or {}
    strategy = agent_reports.get("strategy_report") or {}
    eval_rep = agent_reports.get("evaluation_report") or {}
    risk_breakdown = biz_risk.get("risk_breakdown", {})

    scores = {
        "business_health_score": strategy.get("business_health_score"),
        "business_risk_score": biz_risk.get("business_risk_score"),
        "inventory_risk": risk_breakdown.get("inventory_risk_score"),
        "finance_risk": risk_breakdown.get("finance_risk_score"),
        "supplier_risk": risk_breakdown.get("supplier_risk_score"),
        "compliance_risk": risk_breakdown.get("compliance_risk_score"),
        "confidence_score": eval_rep.get("confidence_score"),
    }

    # --- Extract top recommendations ----------------------------------
    top_recommendations: list[dict[str, Any]] = []
    for rank, key in enumerate(
        ("priority_1_action", "priority_2_action", "priority_3_action"), start=1
    ):
        action = strategy.get(key)
        if action:
            top_recommendations.append({
                "rank": rank,
                "action_title": action.get("action_title", ""),
                "action_description": action.get("action_description", ""),
                "target_domain": action.get("target_domain", ""),
                "urgency": action.get("urgency", ""),
                "expected_impact": action.get("expected_impact", ""),
            })

    # --- Communication draft ------------------------------------------
    comm_draft = agent_reports.get("communication_draft") or {}
    communication_draft = {
        "report_draft": comm_draft.get("report_draft"),
        "email_draft": comm_draft.get("email_draft"),
        "ceo_briefing": comm_draft.get("ceo_briefing"),
        "approval_required": comm_draft.get("approval_required", True),
        "approval_status": state.get("guardrail_state", {}).get(
            "human_approval_status", "pending"
        ),
    }

    # --- Evaluation summary -------------------------------------------
    evaluation = {
        "validation_status": eval_rep.get("validation_status"),
        "human_review_flag": eval_rep.get("human_review_flag"),
        "warnings": eval_rep.get("warnings", []),
    }

    # --- MCP status ---------------------------------------------------
    mcp = state.get("mcp_data", {})
    mcp_status = {
        "google_sheets_mcp": mcp.get("google_sheets_mcp_status", "pending"),
        "calendar_mcp": mcp.get("calendar_mcp_status", "pending"),
        "news_mcp": mcp.get("news_mcp_status", "pending"),
        "supplier_intelligence_mcp": mcp.get("supplier_intelligence_mcp_status", "pending"),
        "risk_registry_mcp": mcp.get("risk_registry_mcp_status", "pending"),
    }

    # --- Execution metadata -------------------------------------------
    execution_metadata = {
        "pipeline_duration_ms": None,
        "agent_execution_times_ms": {},
        "mcp_execution_times_ms": {},
        "errors": [
            e if isinstance(e, dict) else {"error_message": str(e)}
            for e in state.get("errors", [])
        ],
    }

    # --- Error block --------------------------------------------------
    error_block: dict[str, Any] = {
        "error_code": None,
        "error_message": None,
        "failed_agent": None,
        "failed_mcp": None,
    }

    errors = state.get("errors", [])
    if errors and state.get("system_status") == "error":
        last_error = errors[-1] if isinstance(errors[-1], dict) else {}
        error_block["error_code"] = last_error.get("error_code")
        error_block["error_message"] = last_error.get("error_message")
        error_block["failed_agent"] = last_error.get("agent")
        error_block["failed_mcp"] = last_error.get("mcp")

    # --- Assemble final payload (§12.1) -------------------------------
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "run_id": state.get("run_id"),
        "system_status": state.get("system_status", "error"),
        "business_name": state.get("business_name"),
        "business_type": state.get("business_type"),
        "generated_at": now,
        "completed_at": state.get("completed_at"),
        "scores": scores,
        "top_recommendations": top_recommendations,
        "risk_trend": biz_risk.get("risk_trend"),
        "critical_risks": biz_risk.get("critical_risks", []),
        "communication_draft": communication_draft,
        "evaluation": evaluation,
        "mcp_status": mcp_status,
        "execution_metadata": execution_metadata,
        "error": error_block,
    }


def _error_payload(
    error_code: str,
    error_message: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build a minimal error dashboard payload for early validation failures."""
    return {
        "run_id": run_id,
        "system_status": "error",
        "business_name": None,
        "business_type": None,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": None,
        "scores": {
            "business_health_score": None,
            "business_risk_score": None,
            "inventory_risk": None,
            "finance_risk": None,
            "supplier_risk": None,
            "compliance_risk": None,
            "confidence_score": None,
        },
        "top_recommendations": [],
        "risk_trend": None,
        "critical_risks": [],
        "communication_draft": None,
        "evaluation": None,
        "mcp_status": None,
        "execution_metadata": {"errors": []},
        "error": {
            "error_code": error_code,
            "error_message": error_message,
            "failed_agent": None,
            "failed_mcp": None,
        },
    }

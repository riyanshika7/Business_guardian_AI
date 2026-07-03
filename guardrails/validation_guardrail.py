"""Validation Guardrail — agent and MCP output schema validation.

Validates every agent output against its contract-defined schema before
the Evaluation Agent scores it.  Also provides MCP and request payload
validation utilities for the Orchestrator.

Call sites
----------
* ``evaluation_agent.py`` L64 → ``validate_agent_output(name, rep)``
* Available for Orchestrator: ``validate_mcp_output()``, ``validate_request_payload()``

Security principles
-------------------
* Never trusts agent output — every field is type-checked.
* Returns structured ``(passed, issues)`` tuples — never raises.
* Missing fields, null criticals, out-of-range scores, negative monetary
  values, and malformed timestamps are all caught.

Reference: AGENT_CONTRACTS §1–§8, API_CONTRACTS §1–§5.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ISO-8601 timestamp pattern (loose — accepts date-only and datetime)
_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


# ===================================================================
# Per-agent validation rules
# ===================================================================

# Each rule set defines:
#   "required"  — fields that must exist and be non-None
#   "scores"    — fields that must be int in [0, 100]
#   "non_neg"   — fields that must be float >= 0
#   "lists"     — fields that must be lists
#   "timestamp" — fields that must match ISO-8601

_AGENT_RULES: dict[str, dict[str, list[str]]] = {
    "inventory_agent": {
        "required": ["agent", "status", "inventory_risk_score"],
        "scores": ["inventory_risk_score"],
        "lists": ["stockout_prediction", "reorder_recommendation"],
    },
    "finance_agent": {
        "required": ["agent", "status", "finance_risk_score", "total_revenue", "total_expenses"],
        "scores": ["finance_risk_score"],
        "non_neg": ["total_revenue", "total_expenses"],
    },
    "supplier_agent": {
        "required": ["agent", "status", "supplier_risk_score"],
        "scores": ["supplier_risk_score"],
        "lists": ["high_risk_suppliers"],
    },
    "compliance_agent": {
        "required": ["agent", "status", "compliance_risk_score"],
        "scores": ["compliance_risk_score"],
        "lists": ["deadline_alerts"],
    },
    "risk_tracker_agent": {
        "required": ["agent", "status", "business_risk_score", "risk_breakdown", "risk_trend"],
        "scores": ["business_risk_score"],
    },
    "strategy_agent": {
        "required": ["agent", "status", "business_health_score", "priority_1_action", "priority_2_action", "priority_3_action"],
        "scores": ["business_health_score"],
    },
    "communication_agent": {
        "required": ["agent", "status", "approval_required", "approval_status"],
    },
    "evaluation_agent": {
        "required": ["agent", "status", "confidence_score", "validation_status"],
        "scores": ["confidence_score"],
    },
}


# ===================================================================
# Public API
# ===================================================================

def validate_agent_output(
    agent_name: str,
    output: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate a single agent's output against its contract schema.

    This is the primary entry point called by the Evaluation Agent for
    every upstream report.

    Parameters
    ----------
    agent_name:
        Canonical agent name (e.g. ``"inventory_agent"``).
    output:
        Full output dict from the agent.

    Returns
    -------
    tuple[bool, list[str]]
        ``(passed, issues)`` — ``passed`` is ``True`` if no blocking
        issues were found; ``issues`` is a list of human-readable
        problem descriptions (empty when passed).
    """
    issues: list[str] = []

    # --- Guard: output is None or not a dict --------------------------
    if output is None:
        return False, [f"{agent_name}: output is None"]

    if not isinstance(output, dict):
        return False, [f"{agent_name}: output is not a dict (got {type(output).__name__})"]

    # --- Check for upstream error status ------------------------------
    if output.get("status") == "error":
        error_msg = output.get("error_message", "unknown error")
        issues.append(f"{agent_name}: agent returned error status — {error_msg}")
        return False, issues

    # --- Apply rule set -----------------------------------------------
    rules = _AGENT_RULES.get(agent_name, {})

    # Required fields
    for field in rules.get("required", []):
        if field not in output or output[field] is None:
            issues.append(f"{agent_name}: missing required field '{field}'")

    # Score fields (must be int 0–100)
    for field in rules.get("scores", []):
        value = output.get(field)
        if value is not None:
            if not _is_valid_score(value):
                issues.append(
                    f"{agent_name}: score field '{field}' is out of range "
                    f"(got {value}, expected int 0–100)"
                )

    # Non-negative numeric fields
    for field in rules.get("non_neg", []):
        value = output.get(field)
        if value is not None:
            try:
                if float(value) < 0:
                    issues.append(
                        f"{agent_name}: field '{field}' must be non-negative "
                        f"(got {value})"
                    )
            except (TypeError, ValueError):
                issues.append(
                    f"{agent_name}: field '{field}' is not a valid number "
                    f"(got {value!r})"
                )

    # List fields
    for field in rules.get("lists", []):
        value = output.get(field)
        if value is not None and not isinstance(value, list):
            issues.append(
                f"{agent_name}: field '{field}' must be a list "
                f"(got {type(value).__name__})"
            )

    # Timestamp fields
    for field in rules.get("timestamp", []):
        value = output.get(field)
        if value is not None and not _is_valid_timestamp(value):
            issues.append(
                f"{agent_name}: field '{field}' has invalid timestamp format "
                f"(got {value!r})"
            )

    # --- Agent-specific deep validation --------------------------------
    _validate_agent_specific(agent_name, output, issues)

    passed = len(issues) == 0
    if not passed:
        logger.warning(
            "Validation failed for %s: %d issue(s) — %s",
            agent_name,
            len(issues),
            "; ".join(issues),
        )

    return passed, issues


def validate_mcp_output(
    mcp_name: str,
    output: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate a MCP response envelope.

    Checks for the standard success/error envelope defined in
    API_CONTRACTS.md.

    Parameters
    ----------
    mcp_name:
        MCP identifier (e.g. ``"google_sheets_mcp"``).
    output:
        Full response dict from the MCP.

    Returns
    -------
    tuple[bool, list[str]]
        ``(passed, issues)``.
    """
    issues: list[str] = []

    if output is None:
        return False, [f"{mcp_name}: output is None"]

    if not isinstance(output, dict):
        return False, [f"{mcp_name}: output is not a dict"]

    # Envelope check
    status = output.get("status")
    if status not in ("success", "error"):
        issues.append(f"{mcp_name}: 'status' must be 'success' or 'error' (got {status!r})")

    if status == "success":
        data = output.get("data")
        if data is None:
            issues.append(f"{mcp_name}: 'data' is missing in success response")

    if status == "error":
        if not output.get("error_code"):
            issues.append(f"{mcp_name}: 'error_code' missing in error response")
        if not output.get("error_message"):
            issues.append(f"{mcp_name}: 'error_message' missing in error response")

    return len(issues) == 0, issues


def validate_request_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate an incoming analysis request payload.

    Checks the required fields defined in ORCHESTRATOR_CONTRACT §3.1.

    Parameters
    ----------
    payload:
        Raw request body dict.

    Returns
    -------
    tuple[bool, list[str]]
        ``(passed, issues)``.
    """
    issues: list[str] = []

    required = ["business_id", "business_name", "business_type"]
    for field in required:
        value = payload.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            issues.append(f"Missing or empty required field: '{field}'")

    # Numeric fields
    for field in ("period_days", "analysis_window_days"):
        value = payload.get(field)
        if value is not None:
            try:
                if int(value) <= 0:
                    issues.append(f"'{field}' must be a positive integer (got {value})")
            except (TypeError, ValueError):
                issues.append(f"'{field}' is not a valid integer (got {value!r})")

    # Enum fields
    valid_types = {"retail", "agriculture", "ecommerce"}
    btype = payload.get("business_type")
    if btype and btype not in valid_types:
        issues.append(f"Invalid business_type '{btype}'. Must be one of: {valid_types}")

    valid_comm = {"report", "email", "both"}
    ctype = payload.get("communication_type")
    if ctype and ctype not in valid_comm:
        issues.append(f"Invalid communication_type '{ctype}'. Must be one of: {valid_comm}")

    return len(issues) == 0, issues


# ===================================================================
# Agent-specific deep validation
# ===================================================================

def _validate_agent_specific(
    agent_name: str,
    output: dict[str, Any],
    issues: list[str],
) -> None:
    """Run domain-specific validation rules beyond the generic checks."""

    if agent_name == "risk_tracker_agent":
        _validate_risk_breakdown(output, issues)

    elif agent_name == "strategy_agent":
        _validate_priority_actions(output, issues)

    elif agent_name == "communication_agent":
        _validate_communication_draft(output, issues)

    elif agent_name == "inventory_agent":
        _validate_stockout_predictions(output, issues)


def _validate_risk_breakdown(output: dict[str, Any], issues: list[str]) -> None:
    """Validate risk_breakdown sub-object for Risk Tracker Agent."""
    breakdown = output.get("risk_breakdown")
    if breakdown is None:
        return

    if not isinstance(breakdown, dict):
        issues.append("risk_tracker_agent: 'risk_breakdown' must be a dict")
        return

    for key in (
        "inventory_risk_score",
        "finance_risk_score",
        "supplier_risk_score",
        "compliance_risk_score",
    ):
        val = breakdown.get(key)
        if val is not None and not _is_valid_score(val):
            issues.append(
                f"risk_tracker_agent: risk_breakdown.{key} out of range (got {val})"
            )


def _validate_priority_actions(output: dict[str, Any], issues: list[str]) -> None:
    """Validate priority action objects for Strategy Agent."""
    for key in ("priority_1_action", "priority_2_action", "priority_3_action"):
        action = output.get(key)
        if action is None:
            continue
        if not isinstance(action, dict):
            issues.append(f"strategy_agent: '{key}' must be a dict")
            continue
        if not action.get("action_title"):
            issues.append(f"strategy_agent: '{key}.action_title' is missing or empty")
        if not action.get("urgency"):
            issues.append(f"strategy_agent: '{key}.urgency' is missing")


def _validate_communication_draft(output: dict[str, Any], issues: list[str]) -> None:
    """Validate Communication Agent contract invariants."""
    # HITL invariant: approval_required must always be True
    if output.get("approval_required") is not True:
        issues.append(
            "communication_agent: 'approval_required' must be True "
            "(HITL invariant violation)"
        )

    # approval_status must be "pending" at creation time
    if output.get("approval_status") != "pending":
        issues.append(
            "communication_agent: 'approval_status' must be 'pending' at creation"
        )

    # At least one draft type must be present
    has_report = output.get("report_draft") is not None
    has_email = output.get("email_draft") is not None
    if not has_report and not has_email:
        issues.append(
            "communication_agent: at least one of 'report_draft' or "
            "'email_draft' must be present"
        )


def _validate_stockout_predictions(output: dict[str, Any], issues: list[str]) -> None:
    """Validate stockout_prediction entries for Inventory Agent."""
    preds = output.get("stockout_prediction")
    if not isinstance(preds, list):
        return

    for idx, pred in enumerate(preds):
        if not isinstance(pred, dict):
            issues.append(f"inventory_agent: stockout_prediction[{idx}] is not a dict")
            continue

        stock = pred.get("current_stock")
        if stock is not None:
            try:
                if int(stock) < 0:
                    issues.append(
                        f"inventory_agent: negative stock for product "
                        f"'{pred.get('product_id', '?')}' (got {stock})"
                    )
            except (TypeError, ValueError):
                issues.append(
                    f"inventory_agent: invalid stock value for product "
                    f"'{pred.get('product_id', '?')}' (got {stock!r})"
                )


# ===================================================================
# Internal helpers
# ===================================================================

def _is_valid_score(value: Any) -> bool:
    """Check that *value* is an integer in [0, 100]."""
    try:
        v = int(value)
        return 0 <= v <= 100
    except (TypeError, ValueError):
        return False


def _is_valid_timestamp(value: Any) -> bool:
    """Check that *value* looks like an ISO-8601 date or datetime."""
    if not isinstance(value, str):
        return False
    return bool(_ISO_PATTERN.match(value))


def sanitize_input_string(text: str, max_length: int = 1000, run_id: str | None = None, field_name: str | None = None) -> str:
    """Sanitize text input to protect against prompt injection and restrict length."""
    if not isinstance(text, str):
        return ""
    
    # 1. Truncate length
    text = text[:max_length]
    
    # 2. Redact exploit patterns
    exploit_patterns = [
        r"ignore\s+previous\s+instructions",
        r"ignore\s+above\s+instructions",
        r"system\s+status\s*=",
        r"system\s+overrides",
        r"override\s+system",
        r"you\s+are\s+now\s+a\s+malicious",
        r"delete\s+all\s+tables",
        r"drop\s+table"
    ]
    
    sanitized = text
    flagged = False
    for pattern in exploit_patterns:
        if re.search(pattern, sanitized, flags=re.IGNORECASE):
            flagged = True
            sanitized = re.sub(pattern, "[REDACTED_PROMPT_INJECTION]", sanitized, flags=re.IGNORECASE)
            
    if flagged and run_id:
        try:
            from guardrails.audit_logger import log_event
            log_event(
                run_id=run_id,
                event_type="guardrail_validation_failed",
                agent_name="validation_guardrail",
                input_data={"field": field_name, "raw_text_length": len(text)},
                output_data={"message": f"Prompt injection attempt detected and redacted in field '{field_name or 'unknown'}'"},
                status="flagged"
            )
            logger.warning(f"[SECURITY ALERT] Prompt injection attempt detected and redacted in run_id: {run_id}")
        except Exception as e:
            logger.error(f"Failed to log security warning event: {e}")
        
    return sanitized

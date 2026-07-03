"""Confidence Guardrail — pipeline confidence scoring and escalation policy.

Computes a holistic confidence score (0–100) for the entire analysis run
based on the quality of data, agent execution outcomes, and validation
results.  When the score falls below the configured threshold, the
pipeline's ``system_status`` is set to ``"human_review_required"``.

Scoring policy (deductions from a perfect 100)
-----------------------------------------------
* Missing MCP data          → −15  per affected MCP
* Agent timeout / error     → −20  per agent
* Validation warning        → −10  per warning
* Validation failure        → −25  per failed agent
* Conflicting risk reports  → −15  (domain scores diverge by > 40 pts)
* Missing critical agent    → −25  per missing report

Call sites
----------
* ``evaluation_agent.py`` L111 → ``compute_confidence_score(validation_details)``
* Available for Orchestrator:    ``requires_human_review()``, ``calculate_confidence()``,
                                  ``generate_confidence_report()``

Reference: ORCHESTRATOR_CONTRACT §9.3 — Confidence-Based Escalation.
"""

from __future__ import annotations

import logging
from typing import Any

from config import CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# ===================================================================
# Penalty constants
# ===================================================================

_PENALTY_MISSING_MCP: int = 15
_PENALTY_AGENT_ERROR: int = 20
_PENALTY_VALIDATION_WARNING: int = 10
_PENALTY_VALIDATION_FAILURE: int = 25
_PENALTY_CONFLICTING_REPORTS: int = 15
_PENALTY_MISSING_AGENT: int = 25


# ===================================================================
# Public API
# ===================================================================

def compute_confidence_score(
    validation_details: list[dict[str, Any]],
) -> int:
    """Compute pipeline confidence from per-agent validation results.

    This is the primary entry point called by the Evaluation Agent.
    It examines the validation_details list produced by iterating
    ``validate_agent_output`` over all upstream reports.

    Scoring algorithm:
    1. Start at 100.
    2. For each agent whose ``validation_passed`` is ``False`` → −25.
    3. For each agent with non-empty ``issues_found`` but still passed → −10.
    4. Clamp result to [0, 100].

    Parameters
    ----------
    validation_details:
        List of dicts, each containing:
        ``{"agent_name": str, "validation_passed": bool, "issues_found": list}``.

    Returns
    -------
    int
        Confidence score in [0, 100].
    """
    score: float = 100.0

    for detail in (validation_details or []):
        passed = detail.get("validation_passed", True)
        issues = detail.get("issues_found") or []

        if not passed:
            score -= _PENALTY_VALIDATION_FAILURE
        elif len(issues) > 0:
            # Passed but with warnings
            score -= _PENALTY_VALIDATION_WARNING

    return _clamp(score)


def calculate_confidence(
    validation_details: list[dict[str, Any]] | None = None,
    mcp_statuses: dict[str, str] | None = None,
    agent_reports: dict[str, Any] | None = None,
) -> int:
    """Full-spectrum confidence calculation using all available signals.

    This is a richer alternative to ``compute_confidence_score`` that
    the Orchestrator can call directly when it has access to the full
    shared state.

    Penalties applied:
    * Missing / failed MCP       → −15 each
    * Missing agent report       → −25 each
    * Agent returned error       → −20 each
    * Validation failures        → −25 each
    * Validation warnings        → −10 each
    * Conflicting domain scores  → −15 (if any pair diverges > 40)

    Parameters
    ----------
    validation_details:
        Per-agent validation results (same as ``compute_confidence_score``).
    mcp_statuses:
        Dict of MCP name → status string (``"success"``, ``"error"``,
        ``"degraded"``, ``"pending"``, ``"skipped"``).
    agent_reports:
        Dict of report name → agent output dict or ``None``.

    Returns
    -------
    int
        Confidence score in [0, 100].
    """
    score: float = 100.0
    deductions: list[str] = []

    # --- MCP penalties ------------------------------------------------
    if mcp_statuses:
        for mcp_name, status in mcp_statuses.items():
            if status in ("error", "skipped"):
                score -= _PENALTY_MISSING_MCP
                deductions.append(f"MCP '{mcp_name}' status={status} (−{_PENALTY_MISSING_MCP})")

    # --- Agent report penalties ---------------------------------------
    critical_agents = [
        "inventory_risk_report",
        "finance_risk_report",
        "supplier_risk_report",
        "compliance_risk_report",
        "business_risk_report",
        "strategy_report",
        "communication_draft",
    ]

    if agent_reports:
        for key in critical_agents:
            report = agent_reports.get(key)
            if report is None:
                score -= _PENALTY_MISSING_AGENT
                deductions.append(f"Missing agent report '{key}' (−{_PENALTY_MISSING_AGENT})")
            elif isinstance(report, dict) and report.get("status") == "error":
                score -= _PENALTY_AGENT_ERROR
                deductions.append(f"Agent report '{key}' has error status (−{_PENALTY_AGENT_ERROR})")

    # --- Validation penalties -----------------------------------------
    if validation_details:
        for detail in validation_details:
            passed = detail.get("validation_passed", True)
            issues = detail.get("issues_found") or []
            name = detail.get("agent_name", "unknown")

            if not passed:
                score -= _PENALTY_VALIDATION_FAILURE
                deductions.append(f"Validation failed for '{name}' (−{_PENALTY_VALIDATION_FAILURE})")
            elif len(issues) > 0:
                score -= _PENALTY_VALIDATION_WARNING
                deductions.append(f"Validation warnings for '{name}' (−{_PENALTY_VALIDATION_WARNING})")

    # --- Conflicting reports penalty ----------------------------------
    if agent_reports:
        score_keys = {
            "inventory_risk_report": "inventory_risk_score",
            "finance_risk_report": "finance_risk_score",
            "supplier_risk_report": "supplier_risk_score",
            "compliance_risk_report": "compliance_risk_score",
        }
        domain_scores: list[int] = []
        for report_key, score_field in score_keys.items():
            report = agent_reports.get(report_key)
            if isinstance(report, dict):
                val = report.get(score_field)
                if val is not None:
                    try:
                        domain_scores.append(int(val))
                    except (TypeError, ValueError):
                        pass

        if len(domain_scores) >= 2:
            spread = max(domain_scores) - min(domain_scores)
            if spread > 40:
                score -= _PENALTY_CONFLICTING_REPORTS
                deductions.append(
                    f"Domain score spread is {spread} points (−{_PENALTY_CONFLICTING_REPORTS})"
                )

    if deductions:
        logger.info(
            "Confidence deductions: %s → score=%d",
            "; ".join(deductions),
            _clamp(score),
        )

    return _clamp(score)


def requires_human_review(confidence_score: int) -> bool:
    """Check whether the confidence score triggers human review.

    Parameters
    ----------
    confidence_score:
        Pipeline confidence score (0–100).

    Returns
    -------
    bool
        ``True`` if the score is below ``CONFIDENCE_THRESHOLD`` (default 60).
    """
    return confidence_score < CONFIDENCE_THRESHOLD


def generate_confidence_report(
    confidence_score: int,
    validation_details: list[dict[str, Any]] | None = None,
    mcp_statuses: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a structured confidence report for the dashboard.

    Parameters
    ----------
    confidence_score:
        The computed confidence score.
    validation_details:
        Per-agent validation results.
    mcp_statuses:
        Per-MCP status strings.

    Returns
    -------
    dict
        Report dict with keys: ``score``, ``threshold``, ``passed``,
        ``human_review_required``, ``breakdown``.
    """
    breakdown: list[dict[str, Any]] = []

    # Validation breakdown
    if validation_details:
        for detail in validation_details:
            name = detail.get("agent_name", "unknown")
            passed = detail.get("validation_passed", True)
            issues = detail.get("issues_found") or []
            breakdown.append({
                "component": name,
                "type": "agent_validation",
                "passed": passed,
                "issue_count": len(issues),
                "issues": issues,
            })

    # MCP breakdown
    if mcp_statuses:
        for mcp_name, status in mcp_statuses.items():
            breakdown.append({
                "component": mcp_name,
                "type": "mcp_status",
                "passed": status in ("success", "degraded"),
                "status": status,
            })

    return {
        "score": confidence_score,
        "threshold": CONFIDENCE_THRESHOLD,
        "passed": confidence_score >= CONFIDENCE_THRESHOLD,
        "human_review_required": confidence_score < CONFIDENCE_THRESHOLD,
        "breakdown": breakdown,
    }


# ===================================================================
# Internal helpers
# ===================================================================

def _clamp(score: float, lo: int = 0, hi: int = 100) -> int:
    """Clamp *score* to [lo, hi] and cast to int."""
    return max(lo, min(hi, int(score)))

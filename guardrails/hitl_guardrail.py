"""HITL Guardrail — Human-In-The-Loop approval gate for Business Guardian AI.

Manages the mandatory pause between the Communication Agent's output and
the Evaluation Agent's execution.  No communication is sent externally
until a human explicitly approves the draft.

Call sites
----------
* ``workflow.py``  L334  → ``create_hitl_pending_state(res, run_id)``
* ``workflow.py``  L352  → ``reject(approval_id)``
* ``workflow.py``  L367  → ``approve(approval_id)``

Security principles
-------------------
* Approval state is stored in-memory (process-scoped) for V1.
* ``approve`` / ``reject`` validate that the approval_id exists and is
  still in ``pending`` state — double-approve is rejected.
* All state transitions are timestamped for auditability.

Reference: ORCHESTRATOR_CONTRACT §9.1 — HITL Enforcement.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ===================================================================
# In-memory approval registry (keyed by approval_id)
# ===================================================================

_approval_registry: dict[str, dict[str, Any]] = {}


# ===================================================================
# Public API (called by workflow.py)
# ===================================================================

def create_hitl_pending_state(
    communication_output: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    """Create a pending HITL approval record for a communication draft.

    Called after the Communication Agent completes successfully.  Returns
    a state dict containing the generated ``approval_id`` which the
    Orchestrator caches in the shared state's ``guardrail_state``.

    Parameters
    ----------
    communication_output:
        Full output dict from the Communication Agent.
    run_id:
        Pipeline run identifier.

    Returns
    -------
    dict
        HITL state dict with keys: ``approval_id``, ``run_id``,
        ``status``, ``created_at``, ``draft_summary``.
    """
    approval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Extract a short summary for display
    draft_summary = _extract_draft_summary(communication_output)

    record: dict[str, Any] = {
        "approval_id": approval_id,
        "run_id": run_id,
        "status": "pending",
        "created_at": now,
        "decided_at": None,
        "approver": None,
        "decision": None,
        "comments": None,
        "draft_summary": draft_summary,
    }

    _approval_registry[approval_id] = record

    logger.info(
        "HITL approval gate opened — approval_id=%s run_id=%s",
        approval_id,
        run_id,
    )

    return record


def approve(
    approval_id: str,
    approver: str = "dashboard_user",
    comments: str | None = None,
) -> dict[str, Any]:
    """Record an approval decision for the given HITL gate.

    Parameters
    ----------
    approval_id:
        Identifier returned by ``create_hitl_pending_state``.
    approver:
        Identifier of the human who approved (default: ``"dashboard_user"``).
    comments:
        Optional free-text review comments.

    Returns
    -------
    dict
        Updated HITL record.

    Raises
    ------
    ValueError
        If ``approval_id`` is not found or is not in ``pending`` state.
    """
    return _record_decision(approval_id, "approved", approver, comments)


def reject(
    approval_id: str,
    approver: str = "dashboard_user",
    comments: str | None = None,
) -> dict[str, Any]:
    """Record a rejection decision for the given HITL gate.

    Parameters
    ----------
    approval_id:
        Identifier returned by ``create_hitl_pending_state``.
    approver:
        Identifier of the human who rejected.
    comments:
        Optional free-text rejection reason.

    Returns
    -------
    dict
        Updated HITL record.

    Raises
    ------
    ValueError
        If ``approval_id`` is not found or is not in ``pending`` state.
    """
    return _record_decision(approval_id, "rejected", approver, comments)


# ===================================================================
# Query helpers
# ===================================================================

def check_approval_required(run_id: str) -> bool:
    """Check whether a given run has an outstanding HITL gate.

    Returns ``True`` if any pending approval exists for the run.
    """
    for record in _approval_registry.values():
        if record["run_id"] == run_id and record["status"] == "pending":
            return True
    return False


def get_approval_status(approval_id: str) -> dict[str, Any] | None:
    """Retrieve the current state of a HITL approval record.

    Returns ``None`` if the approval_id is not found.
    """
    return _approval_registry.get(approval_id)


def pause_for_review(run_id: str) -> dict[str, Any] | None:
    """Retrieve the pending HITL record for a run, if one exists.

    Convenience wrapper used by the dashboard to display the
    draft-for-review UI.
    """
    for record in _approval_registry.values():
        if record["run_id"] == run_id and record["status"] == "pending":
            return record
    return None


# ===================================================================
# Internal helpers
# ===================================================================

def _record_decision(
    approval_id: str,
    decision: str,
    approver: str,
    comments: str | None,
) -> dict[str, Any]:
    """Internal state-transition handler for approve/reject."""
    record = _approval_registry.get(approval_id)

    if record is None:
        raise ValueError(f"HITL approval_id '{approval_id}' not found.")

    if record["status"] != "pending":
        raise ValueError(
            f"HITL approval_id '{approval_id}' is already "
            f"'{record['status']}' — cannot transition to '{decision}'."
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    record["status"] = decision
    record["decision"] = decision
    record["decided_at"] = now
    record["approver"] = approver
    record["comments"] = comments

    logger.info(
        "HITL decision recorded — approval_id=%s decision=%s approver=%s",
        approval_id,
        decision,
        approver,
    )

    return record


def _extract_draft_summary(communication_output: dict[str, Any]) -> str:
    """Build a one-line summary from the Communication Agent output."""
    try:
        report = communication_output.get("report_draft") or {}
        title = report.get("title", "")
        email = communication_output.get("email_draft") or {}
        subject = email.get("subject", "")

        parts = [p for p in (title, subject) if p]
        if parts:
            return " | ".join(parts)

        return "Communication draft awaiting review"
    except Exception:
        return "Communication draft awaiting review"

"""Audit Logger — structured event logging for Business Guardian AI.

Writes every significant pipeline event to **two sinks** simultaneously:

1. **Rotating log file** — ``logs/audit.log`` (human-readable, grep-friendly)
2. **SQLite table**      — ``audit_logs`` (queryable, dashboard-consumable)

The logger is designed for **failure isolation**: if the database write
fails, the file log still captures the event, and the pipeline is never
interrupted.

Call sites
----------
* ``orchestrator.py``  → pipeline lifecycle events
* ``workflow.py``      → MCP calls, agent dispatches, guardrail events

Schema reference: DATA_MODELS §16 — AuditLog.
Table reference:  database/schema.sql — audit_logs.

Security principles
-------------------
* All payloads are serialised to JSON strings before storage to prevent
  injection via crafted dict values.
* Timestamps are always UTC ISO-8601.
* ``log_event`` never raises — errors are captured to stderr only.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any

from config import PROJECT_ROOT
from database import db

# ===================================================================
# Module-level audit logger (file sink)
# ===================================================================

_LOG_DIR: str = os.path.join(str(PROJECT_ROOT), "logs")
_LOG_FILE: str = os.path.join(_LOG_DIR, "audit.log")

# Ensure the logs directory exists
os.makedirs(_LOG_DIR, exist_ok=True)

# Create a dedicated logger (separate from the root logger)
_audit_logger: logging.Logger = logging.getLogger("guardian.audit")
_audit_logger.setLevel(logging.INFO)
_audit_logger.propagate = False  # Don't bubble up to root

# Rotating file handler: 5 MB max, keep 5 backups
if not _audit_logger.handlers:
    _file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    _file_handler.formatter.converter = lambda *_: datetime.now(timezone.utc).timetuple()
    _audit_logger.addHandler(_file_handler)

# Standard application logger for internal warnings
logger = logging.getLogger(__name__)


# ===================================================================
# Public API
# ===================================================================

def log_event(
    run_id: str,
    event_type: str,
    *,
    agent_name: str | None = None,
    input_payload: dict[str, Any] | None = None,
    output_payload: dict[str, Any] | None = None,
    status: str = "success",
    error_code: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Record a single audit event to the log file and SQLite database.

    This function **never raises**.  If the database insert fails, the
    event is still written to the log file and a warning is emitted.

    Parameters
    ----------
    run_id:
        Pipeline run identifier (UUID).
    event_type:
        Machine-readable event category.  Permitted values include:
        ``pipeline_start``, ``pipeline_complete``, ``pipeline_error``,
        ``mcp_call_start``, ``mcp_call_complete``, ``mcp_call_error``,
        ``agent_dispatch``, ``agent_complete``, ``agent_error``,
        ``guardrail_hitl_pending``, ``guardrail_hitl_approved``,
        ``guardrail_hitl_rejected``, ``guardrail_validation_failed``,
        ``guardrail_confidence_flagged``.
    agent_name:
        Name of the agent or MCP that produced this event (nullable).
    input_payload:
        Serialisable input passed to the component (nullable).
    output_payload:
        Serialisable output received from the component (nullable).
    status:
        Outcome: ``"success"``, ``"error"``, ``"retry"``, or ``"skipped"``.
    error_code:
        Structured error code if status is ``"error"`` (nullable).
    duration_ms:
        Execution duration in milliseconds (nullable).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- 1. File log (always) -----------------------------------------
    try:
        log_parts = [
            f"run_id={run_id}",
            f"event={event_type}",
            f"status={status}",
        ]
        if agent_name:
            log_parts.append(f"agent={agent_name}")
        if error_code:
            log_parts.append(f"error_code={error_code}")
        if duration_ms is not None:
            log_parts.append(f"duration_ms={duration_ms}")

        _audit_logger.info(" | ".join(log_parts))
    except Exception:
        # Last resort: stderr
        logger.warning("Failed to write audit event to log file", exc_info=True)

    # --- 2. SQLite (best effort) --------------------------------------
    try:
        log_id = str(uuid.uuid4())
        row: dict[str, Any] = {
            "log_id": log_id,
            "run_id": run_id,
            "event_type": event_type,
            "agent_name": agent_name,
            "input_payload": _safe_json(input_payload),
            "output_payload": _safe_json(output_payload),
            "status": status,
            "error_code": error_code,
            "duration_ms": duration_ms,
            "timestamp": timestamp,
        }
        db.insert_row("audit_logs", row)
    except Exception:
        logger.warning(
            "Failed to persist audit event to SQLite — run_id=%s event=%s",
            run_id,
            event_type,
            exc_info=True,
        )


def get_run_history(run_id: str) -> list[dict[str, Any]]:
    """Retrieve all audit log entries for a specific pipeline run.

    Parameters
    ----------
    run_id:
        Pipeline run identifier.

    Returns
    -------
    list[dict]
        Chronologically ordered audit events for the run.
    """
    try:
        return db.fetch_all(
            "SELECT * FROM audit_logs WHERE run_id = ? ORDER BY timestamp ASC",
            (run_id,),
        )
    except Exception:
        logger.warning("Failed to query run history for run_id=%s", run_id, exc_info=True)
        return []


def get_error_history(run_id: str | None = None) -> list[dict[str, Any]]:
    """Retrieve all error-status audit events, optionally filtered by run.

    Parameters
    ----------
    run_id:
        If provided, only errors for this run are returned.

    Returns
    -------
    list[dict]
        Error events ordered by timestamp descending (most recent first).
    """
    try:
        if run_id:
            return db.fetch_all(
                "SELECT * FROM audit_logs WHERE status = 'error' AND run_id = ? "
                "ORDER BY timestamp DESC",
                (run_id,),
            )
        return db.fetch_all(
            "SELECT * FROM audit_logs WHERE status = 'error' ORDER BY timestamp DESC",
        )
    except Exception:
        logger.warning("Failed to query error history", exc_info=True)
        return []


# ===================================================================
# Internal helpers
# ===================================================================

def _safe_json(payload: Any) -> str | None:
    """Serialise a payload to a JSON string, returning None on failure."""
    if payload is None:
        return None
    try:
        return json.dumps(payload, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps({"_serialisation_error": str(payload)})

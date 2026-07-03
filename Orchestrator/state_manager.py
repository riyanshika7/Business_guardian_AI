"""Centralized shared-state models for the Business Guardian AI orchestrator.

Every model in this module maps directly to the Shared State Contract
defined in ORCHESTRATOR_CONTRACT.md §5.  The Orchestrator instantiates
a single ``SharedState`` object at the start of each analysis run and
mutates it exclusively — agents never touch shared state directly.

Sub-models
----------
* ``MCPData``          — validated MCP response payloads + per-MCP status flags
* ``AgentReports``     — slots for the eight agent output payloads
* ``GuardrailState``   — HITL, validation, and confidence gate flags
* ``ExecutionError``   — structured non-fatal error record
* ``ExecutionMetadata``— timing telemetry, pipeline status, and error log

Reference documents
-------------------
* ORCHESTRATOR_CONTRACT.md  §5  (Shared State Contract)
* ORCHESTRATOR_CONTRACT.md  §7  (MCP Orchestration Rules)
* ORCHESTRATOR_CONTRACT.md  §9  (Guardrail Enforcement Rules)
* ORCHESTRATOR_CONTRACT.md  §12 (Dashboard Response Contract)
* API_CONTRACTS.md          §1–5 (MCP output schemas)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ===================================================================
# Enumerations — constrain string fields to permitted contract values
# ===================================================================

class MCPStatus(str, Enum):
    """Per-MCP execution outcome.

    ORCHESTRATOR_CONTRACT §5 — mcp_data status fields.
    """

    SUCCESS = "success"
    ERROR = "error"
    DEGRADED = "degraded"
    PENDING = "pending"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Top-level pipeline lifecycle state.

    ORCHESTRATOR_CONTRACT §5 — execution_metadata.pipeline_status.
    """

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    DEGRADED = "degraded"
    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class ApprovalStatus(str, Enum):
    """Human-In-The-Loop approval gate state.

    ORCHESTRATOR_CONTRACT §9.1 — guardrail_state.human_approval_status.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ===================================================================
# MCPData — all data retrieved from the five MCP integrations
# ===================================================================

class MCPData(BaseModel):
    """Validated payloads and status flags for all five MCP integrations.

    Populated by the Orchestrator during the MCP Layer phase (Steps 5–10).
    Fields map to ORCHESTRATOR_CONTRACT §7.3 and API_CONTRACTS §1–5.
    """

    # --- Google Sheets MCP (API_CONTRACTS §1) --------------------------
    inventory_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Inventory records from Google Sheets MCP.",
    )
    sales_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sales transaction records from Google Sheets MCP.",
    )
    expenses_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Expense records from Google Sheets MCP.",
    )
    supplier_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Supplier master records from Google Sheets MCP.",
    )

    # --- Calendar MCP (API_CONTRACTS §2) --------------------------------
    compliance_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Calendar events mapped to compliance obligations.",
    )

    # --- News MCP (API_CONTRACTS §3) ------------------------------------
    supplier_news: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Supplier-specific news articles from News MCP.",
    )
    industry_news: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Industry-level news articles from News MCP.",
    )

    # --- Supplier Intelligence MCP (API_CONTRACTS §4) -------------------
    supplier_intelligence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Raw enriched supplier data bundle from Supplier Intelligence MCP.",
    )
    supplier_profiles: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Enriched vendor profiles (supplier_intelligence_mcp.data.supplier_profiles).",
    )
    supplier_risk_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Pre-computed supplier risk assessments (supplier_intelligence_mcp.data.supplier_risk_data).",
    )

    # --- Risk Registry MCP (API_CONTRACTS §5) ---------------------------
    risk_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Historical risk score time-series from Risk Registry MCP.",
    )
    risk_status: dict[str, Any] = Field(
        default_factory=dict,
        description="Latest aggregate risk posture snapshot.",
    )
    risk_trends: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Multi-period trend direction indicators.",
    )

    # --- Per-MCP execution status flags ---------------------------------
    google_sheets_mcp_status: MCPStatus = Field(
        default=MCPStatus.PENDING,
        description="Google Sheets MCP outcome. FAIL = HALT pipeline.",
    )
    calendar_mcp_status: MCPStatus = Field(
        default=MCPStatus.PENDING,
        description="Calendar MCP outcome. FAIL = HALT pipeline.",
    )
    news_mcp_status: MCPStatus = Field(
        default=MCPStatus.PENDING,
        description="News MCP outcome. FAIL = DEGRADE + CONTINUE.",
    )
    supplier_intelligence_mcp_status: MCPStatus = Field(
        default=MCPStatus.PENDING,
        description="Supplier Intelligence MCP outcome. FAIL = HALT pipeline.",
    )
    risk_registry_mcp_status: MCPStatus = Field(
        default=MCPStatus.PENDING,
        description="Risk Registry MCP outcome. FAIL = DEGRADE + CONTINUE.",
    )


# ===================================================================
# AgentReports — slots for all eight agent outputs
# ===================================================================

class AgentReports(BaseModel):
    """Structured JSON outputs from each agent in the pipeline.

    Fields begin as ``None`` and are populated by the Orchestrator as
    each agent completes.  ORCHESTRATOR_CONTRACT §5 — agent_reports.
    """

    inventory_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Inventory Agent (AGENT_CONTRACTS §1).",
    )
    finance_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Finance Agent (AGENT_CONTRACTS §2).",
    )
    supplier_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Supplier Agent (AGENT_CONTRACTS §3).",
    )
    compliance_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Compliance Agent (AGENT_CONTRACTS §4).",
    )
    business_risk_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Risk Tracker Agent (AGENT_CONTRACTS §5).",
    )
    strategy_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Strategy Agent (AGENT_CONTRACTS §6).",
    )
    communication_draft: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Communication Agent (AGENT_CONTRACTS §7).",
    )
    evaluation_report: dict[str, Any] | None = Field(
        default=None,
        description="Full output from Evaluation Agent (AGENT_CONTRACTS §8).",
    )


# ===================================================================
# GuardrailState — enforcement flags for all four guardrails
# ===================================================================

class GuardrailState(BaseModel):
    """Runtime state of all guardrail enforcement gates.

    Updated exclusively by the Orchestrator.
    ORCHESTRATOR_CONTRACT §9 — Guardrail Enforcement Rules.
    """

    # HITL gate (§9.1) — always true; Communication Agent output requires
    # explicit human approval before Evaluation Agent may execute.
    human_approval_required: bool = Field(
        default=True,
        description="Always True in V1. Communication Agent output requires approval.",
    )
    human_approval_status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Updated only via POST /analyze/approve.",
    )

    # Data validation gate (§9.2) — set after MCP response validation.
    validation_passed: bool | None = Field(
        default=None,
        description="True if all MCP data passed validation; None before validation runs.",
    )

    # Confidence threshold gate (§9.3) — set after Evaluation Agent.
    confidence_threshold_passed: bool | None = Field(
        default=None,
        description="True if confidence_score >= threshold; None before evaluation runs.",
    )


# ===================================================================
# ExecutionError — non-fatal error record
# ===================================================================

class ExecutionError(BaseModel):
    """Structured record for non-fatal errors appended during the run.

    ORCHESTRATOR_CONTRACT §5 — execution_metadata.errors.
    """

    error_code: str = Field(description="Machine-readable error code.")
    error_message: str = Field(description="Human-readable description.")
    source: str = Field(description="Component that produced the error (MCP name, agent name, or 'orchestrator').")
    timestamp: str = Field(description="ISO 8601 UTC timestamp of the error event.")


# ===================================================================
# ExecutionMetadata — timing, status, and error tracking
# ===================================================================

class MCPExecutionTimes(BaseModel):
    """Wall-clock execution durations for each MCP call (milliseconds).

    ORCHESTRATOR_CONTRACT §13.6 — Observability.
    """

    google_sheets_mcp: int | None = None
    calendar_mcp: int | None = None
    news_mcp: int | None = None
    supplier_intelligence_mcp: int | None = None
    risk_registry_mcp: int | None = None


class AgentExecutionTimes(BaseModel):
    """Wall-clock execution durations for each agent call (milliseconds).

    ORCHESTRATOR_CONTRACT §13.6 — Observability.
    """

    inventory_agent: int | None = None
    finance_agent: int | None = None
    supplier_agent: int | None = None
    compliance_agent: int | None = None
    risk_tracker_agent: int | None = None
    strategy_agent: int | None = None
    communication_agent: int | None = None
    evaluation_agent: int | None = None


class ExecutionMetadata(BaseModel):
    """Pipeline-level telemetry, status flag, and cumulative error log.

    ORCHESTRATOR_CONTRACT §5 — execution_metadata.
    """

    run_id: str = Field(description="Duplicated from SharedState for independent serialisation.")
    started_at: str = Field(description="ISO 8601 UTC timestamp of pipeline start.")
    completed_at: str | None = Field(
        default=None,
        description="ISO 8601 UTC timestamp of pipeline completion; None while running.",
    )
    pipeline_status: PipelineStatus = Field(
        default=PipelineStatus.RUNNING,
        description="Current lifecycle state of the pipeline.",
    )
    mcp_execution_times_ms: MCPExecutionTimes = Field(
        default_factory=MCPExecutionTimes,
        description="Per-MCP wall-clock durations in milliseconds.",
    )
    agent_execution_times_ms: AgentExecutionTimes = Field(
        default_factory=AgentExecutionTimes,
        description="Per-agent wall-clock durations in milliseconds.",
    )
    errors: list[ExecutionError] = Field(
        default_factory=list,
        description="Non-fatal errors accumulated during the run.",
    )


# ===================================================================
# SharedState — the single top-level state object per analysis run
# ===================================================================

class SharedState(BaseModel):
    """Top-level shared state for a single Business Guardian AI analysis run.

    Created at the start of every pipeline invocation and mutated only by
    the Orchestrator.  Agents receive extracted copies of relevant fields
    as their inputs — never a reference to this object.

    Matches ORCHESTRATOR_CONTRACT.md §5 verbatim.

    Lifecycle
    ---------
    1. ``POST /analyze``  — Orchestrator creates SharedState, populates it
       through Steps 1–16, then caches it for the HITL pause.
    2. ``POST /analyze/approve`` — Orchestrator retrieves the cached state,
       runs Steps 17–21, then deletes the cache entry.

    The state is never persisted to permanent database tables in raw form.
    Individual agent outputs are written to ``reports`` and ``risk_scores``
    tables via the database helper layer upon pipeline completion.
    """

    # --- Run identity & user request fields (§3.1) ---------------------
    run_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique pipeline run identifier (UUID).",
    )
    business_id: str = Field(description="Unique business entity identifier.")
    business_name: str = Field(description="Human-readable business name.")
    business_type: str = Field(description="One of: retail, agriculture, ecommerce.")
    period_days: int = Field(description="Financial analysis window in days (> 0).")
    analysis_window_days: int = Field(description="Compliance look-ahead in days (> 0).")
    communication_type: str = Field(
        default="both",
        description="Communication Agent mode: 'report', 'email', or 'both'.",
    )
    recipient_name: str | None = Field(
        default=None,
        description="Optional email recipient name for Communication Agent.",
    )

    # --- Composite sub-models ------------------------------------------
    mcp_data: MCPData = Field(
        default_factory=MCPData,
        description="All data retrieved from MCP integrations.",
    )
    agent_reports: AgentReports = Field(
        default_factory=AgentReports,
        description="Structured outputs from all eight agents.",
    )
    guardrail_state: GuardrailState = Field(
        default_factory=GuardrailState,
        description="Runtime state of all guardrail enforcement gates.",
    )
    execution_metadata: ExecutionMetadata = Field(
        default=None,
        description="Timing telemetry, pipeline status, and error log.",
    )

    # --- Pydantic configuration ----------------------------------------
    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        """Auto-populate execution_metadata with run_id and start time."""
        if self.execution_metadata is None:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.execution_metadata = ExecutionMetadata(
                run_id=self.run_id,
                started_at=now,
            )

    # -------------------------------------------------------------------
    # Convenience helpers used by the Orchestrator
    # -------------------------------------------------------------------

    def record_error(
        self,
        error_code: str,
        error_message: str,
        source: str,
    ) -> None:
        """Append a non-fatal error to execution_metadata.errors.

        Parameters
        ----------
        error_code:
            Machine-readable error code (e.g. ``"AUDIT_LOG_WRITE_FAILED"``).
        error_message:
            Human-readable description.
        source:
            Component name (``"news_mcp"``, ``"inventory_agent"``, etc.).
        """
        self.execution_metadata.errors.append(
            ExecutionError(
                error_code=error_code,
                error_message=error_message,
                source=source,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )

    def mark_complete(self, status: PipelineStatus) -> None:
        """Finalise the pipeline run with the given terminal status.

        Sets ``execution_metadata.completed_at`` and ``pipeline_status``.
        """
        self.execution_metadata.completed_at = (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        self.execution_metadata.pipeline_status = status

    @property
    def system_status(self) -> str:
        """Derive the dashboard-facing ``system_status`` string.

        Mapping defined in ORCHESTRATOR_CONTRACT §4.5.
        """
        return self.execution_metadata.pipeline_status.value

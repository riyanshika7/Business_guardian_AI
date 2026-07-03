# ORCHESTRATOR_CONTRACT.md

> **Business Guardian AI — Orchestrator Contract v1.0**  
> This document is binding and consistent with `PROJECT_CONSTITUTION.md`, `TEAM_CONTEXT.md`, `AGENT_CONTRACTS.md`, `DATA_MODELS.md`, and `API_CONTRACTS.md`. Do not modify orchestrator behavior, shared state schema, or execution order without team approval and a constitution amendment.

---

## 1. Purpose

The Orchestrator is the central coordinator of the Business Guardian AI pipeline. It is the single entry point for all analysis runs and the single point of control for the entire agent workflow.

The Orchestrator exists to:

- Receive analysis requests from the Streamlit dashboard or FastAPI endpoints (`/analyze` and `/analyze/approve`) and translate them into a structured pipeline execution.
- Fetch all external data via the MCP Layer before any agent executes, ensuring agents work only with pre-validated, structured inputs.
- Dispatch the four core agents in parallel and manage their concurrent execution safely.
- Pass structured outputs from each completed stage as inputs to the next stage in the sequential pipeline.
- Enforce all guardrails — human-in-the-loop approval, data validation, confidence thresholds, and audit logging — without delegating these responsibilities to individual agents.
- Manage shared state persistence across the two-step asynchronous Human-In-The-Loop execution flow.
- Assemble the final dashboard payload from all agent outputs and return it to the UI.

The Orchestrator does **not** perform business analysis. It does not compute risk scores, generate recommendations, or draft communications. All business logic lives in agents and skills. The Orchestrator's sole responsibility is coordination, sequencing, guardrail enforcement, and state management.

---

## 2. Responsibilities

### 2.1 Request Intake & Workflow Management
- Accept initial analysis requests via the FastAPI `POST /analyze` endpoint or Streamlit dashboard.
- Accept Human-In-The-Loop approval decisions via the `POST /analyze/approve` endpoint to resume paused runs.
- Validate that all required configuration fields (`business_id`, `business_name`, `business_type`, `period_days`, `analysis_window_days`) are present and non-null before beginning the pipeline.
- Generate a unique `run_id` (UUID) for the analysis run. All downstream agent calls, MCP calls, and audit log entries reference this `run_id`.
- Reject invalid requests with a structured error response before any MCP or agent is invoked.

### 2.2 MCP Execution
- Call all five MCPs in sequence before any agent is dispatched.
- Validate each MCP response against the Standard Success/Error Response envelopes defined in `API_CONTRACTS.md`.
- Apply the MCP failure policy (halt or degrade) as defined in Section 7.
- Store all validated MCP responses and execution statuses in the Shared State object.

### 2.3 Shared State Creation & Caching
- Instantiate the Shared State object at the start of each run (see Section 5).
- Populate MCP data fields after MCP execution completes.
- Populate agent report fields as each agent completes.
- Securely cache the Shared State object in active-run storage during the Human-In-The-Loop pause to allow seamless resumption across independent HTTP requests.
- Never allow one agent's execution to mutate another agent's input fields in shared state.

### 2.4 Agent Dispatch
- Dispatch the four parallel agents (Inventory, Finance, Supplier, Compliance) simultaneously after all MCP data is loaded into shared state.
- Dispatch each subsequent sequential agent (Risk Tracker → Strategy → Communication → Evaluation) only after its upstream dependency has completed successfully.
- Pass each agent exactly the inputs defined in `AGENT_CONTRACTS.md`. Do not add or remove fields.

### 2.5 Parallel Execution Management
- Execute Inventory Agent, Finance Agent, Supplier Agent, and Compliance Agent concurrently.
- Wait for all four parallel agents to complete (success or error) before dispatching the Risk Tracker Agent.
- If any parallel agent returns `status: "error"`, halt the pipeline and return a structured error response identifying the failing agent.

### 2.6 Result Aggregation
- Store each agent's structured JSON output in the corresponding field of shared state immediately upon completion.
- Validate that each agent output matches its schema defined in `AGENT_CONTRACTS.md` and `DATA_MODELS.md` before storing.

### 2.7 Guardrail Enforcement
- Enforce the Human-In-The-Loop gate after the Communication Agent produces its draft. The Orchestrator must cache shared state, set `system_status` to `"awaiting_human_approval"`, and return the intermediate payload to the UI. The pipeline resumes to invoke the Evaluation Agent only upon receiving an explicit approval request via `POST /analyze/approve`. See Section 9.
- Enforce the Data Validation guardrail on all incoming MCP data before it enters shared state.
- Enforce the Confidence Threshold guardrail on the Evaluation Agent output. If `confidence_score` < 60, set `system_status` to `"human_review_required"` in the dashboard payload.
- Enforce Audit Logging at every step. See Section 11.

### 2.8 Error Handling
- Apply the error handling policy defined in Section 10 to all MCP failures, agent failures, and unexpected exceptions.
- Never silently swallow errors. Every error must be logged to `audit_logs` and surfaced in the dashboard payload via `system_status` or `execution_metadata.errors`.

### 2.9 Audit Logging
- Write an audit log entry before and after every MCP call, agent call, and guardrail event.
- See Section 11 for required fields and schema.

### 2.10 Dashboard Response Assembly
- After the Evaluation Agent completes (or when pausing for HITL approval), assemble the dashboard payload from shared state.
- Return the dashboard payload to the FastAPI endpoint or directly to the Streamlit dashboard.
- See Section 12 for the required dashboard response schema.

---

## 3. Inputs

### 3.1 User Request

The triggering input to the Orchestrator. Provided by the Streamlit dashboard or FastAPI `/analyze` endpoint.

```json
{
  "business_id": "string",
  "business_name": "string",
  "business_type": "retail | agriculture | ecommerce",
  "period_days": "integer",
  "analysis_window_days": "integer",
  "communication_type": "report | email | both",
  "recipient_name": "string | null"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `business_id` | string | Yes | Unique identifier for the business; used by Risk Registry MCP |
| `business_name` | string | Yes | Human-readable business name; passed to Communication Agent |
| `business_type` | string | Yes | Determines which skills agents invoke; one of the permitted values |
| `period_days` | integer | Yes | Number of days in the financial analysis window; must be > 0 |
| `analysis_window_days` | integer | Yes | Number of days ahead for compliance analysis; must be > 0 |
| `communication_type` | string | Yes | Determines what the Communication Agent drafts |
| `recipient_name` | string or null | No | Optional email recipient name for the Communication Agent |

### 3.2 HITL Approval Request

The triggering input to resume a paused pipeline. Provided by the Streamlit dashboard via FastAPI `POST /analyze/approve`.

```json
{
  "run_id": "string (UUID)",
  "approval_status": "approved | rejected"
}
```

### 3.3 MCP Responses

Structured JSON responses from all five MCPs, validated against the schemas in `API_CONTRACTS.md`. These are not provided externally — the Orchestrator fetches them as part of the pipeline.

### 3.4 Configuration Settings

Loaded from environment variables via `config.py`. The Orchestrator reads:

- `SPREADSHEET_ID` — Google Sheets MCP target
- `CALENDAR_ID` — Calendar MCP target
- `NEWS_MAX_ARTICLES` — Default article cap for News MCP
- `NEWS_MAX_AGE_DAYS` — Default article age limit for News MCP
- `RISK_HISTORY_DAYS` — Default history window for Risk Registry MCP
- `AGENT_TIMEOUT_SECONDS` — Maximum execution time per agent
- `MAX_AGENT_RETRIES` — Maximum retry attempts per agent
- `PIPELINE_TIMEOUT_SECONDS` — Maximum total wall-clock execution time for the pipeline

### 3.5 Guardrail Policies

The Orchestrator enforces the following policy constants, loaded from `config.py`:

| Policy | Value |
|---|---|
| Confidence threshold for human review | 60 |
| Maximum agent timeout | Configurable via `AGENT_TIMEOUT_SECONDS` |
| Maximum agent retries | Configurable via `MAX_AGENT_RETRIES` |
| Maximum pipeline timeout | Configurable via `PIPELINE_TIMEOUT_SECONDS` |
| Human approval required | Always `true` for Communication Agent output |

---

## 4. Outputs

### 4.1 Dashboard Payload

The final assembled response returned to the UI at the end of a successful pipeline run (or intermediate state during HITL pause). Schema defined in Section 12.

### 4.2 Agent Results

All eight agent outputs, stored in shared state and included in the dashboard payload where relevant.

### 4.3 Business Risk Report

The structured output of the Risk Tracker Agent (`BusinessRiskReport`), as defined in `DATA_MODELS.md` and `AGENT_CONTRACTS.md`.

### 4.4 Evaluation Report

The structured output of the Evaluation Agent (`EvaluationReport`), as defined in `DATA_MODELS.md` and `AGENT_CONTRACTS.md`.

### 4.5 System Status

A string field included in every response indicating the current state of the pipeline:

| Value | Meaning |
|---|---|
| `"success"` | Pipeline completed successfully; confidence score >= 60 |
| `"human_review_required"` | Pipeline completed successfully but confidence score < 60 |
| `"awaiting_human_approval"` | Pipeline paused at Communication Agent gate; awaiting explicit human approval |
| `"error"` | Pipeline halted due to a critical failure or human rejection |
| `"degraded"` | Pipeline completed with one or more non-critical MCP failures |

---

## 5. Shared State Contract

The Orchestrator maintains a single Shared State object for each analysis run. This object is created at run start and mutated only by the Orchestrator — never directly by agents. Agents receive their inputs as extracted copies of relevant fields, not references to shared state.

```json
{
  "run_id": "string (UUID)",
  "business_id": "string",
  "business_name": "string",
  "business_type": "string",
  "period_days": "integer",
  "analysis_window_days": "integer",
  "communication_type": "string",
  "recipient_name": "string | null",
  "products": [ ],

  "mcp_data": {
    "inventory_data": [ ],
    "sales_data": [ ],
    "expenses_data": [ ],
    "supplier_data": [ ],
    "compliance_data": [ ],
    "supplier_intelligence": [ ],
    "supplier_news": [ ],
    "risk_history": [ ],
    "risk_status": { },
    "risk_trends": [ ],
    "google_sheets_mcp_status": "success | error | pending | skipped",
    "calendar_mcp_status": "success | error | pending | skipped",
    "supplier_intelligence_mcp_status": "success | error | pending | skipped",
    "news_mcp_status": "success | degraded | pending | skipped",
    "risk_registry_mcp_status": "success | degraded | pending | skipped"
  },

  "agent_reports": {
    "inventory_risk_report": null,
    "finance_risk_report": null,
    "supplier_risk_report": null,
    "compliance_risk_report": null,
    "business_risk_report": null,
    "strategy_report": null,
    "communication_draft": null,
    "evaluation_report": null
  },

  "guardrail_state": {
    "human_approval_required": true,
    "human_approval_status": "pending | approved | rejected",
    "confidence_threshold_passed": null,
    "validation_passed": null
  },

  "execution_metadata": {
    "run_id": "string (UUID)",
    "started_at": "string (ISO 8601)",
    "completed_at": "string (ISO 8601) | null",
    "pipeline_status": "running | success | error | degraded | awaiting_human_approval | human_review_required",
    "mcp_execution_times_ms": {
      "google_sheets_mcp": "integer | null",
      "calendar_mcp": "integer | null",
      "news_mcp": "integer | null",
      "supplier_intelligence_mcp": "integer | null",
      "risk_registry_mcp": "integer | null"
    },
    "agent_execution_times_ms": {
      "inventory_agent": "integer | null",
      "finance_agent": "integer | null",
      "supplier_agent": "integer | null",
      "compliance_agent": "integer | null",
      "risk_tracker_agent": "integer | null",
      "strategy_agent": "integer | null",
      "communication_agent": "integer | null",
      "evaluation_agent": "integer | null"
    },
    "errors": [ ]
  }
}
```

**Rules:**
- `products` is loaded from the local SQLite database during pipeline initialization and stored at the root of the shared state.
- `agent_reports` fields begin as `null` and are populated by the Orchestrator as each agent completes.
- `guardrail_state.human_approval_status` begins as `"pending"` and is updated only when the human provides explicit input via `POST /analyze/approve`.
- `execution_metadata.errors` is an array of structured error objects appended whenever a non-fatal error occurs (degraded MCP, audit log write failure, agent warning).
- Shared state must not be persisted to the permanent database tables in its raw form. It is maintained in an active-run cache/temporary store during the HITL pause. Individual agent outputs are permanently stored in `reports` and `risk_scores` tables via the database helper layer upon pipeline completion.

---

## 6. Execution Workflow

### 6.1 ASCII Workflow Diagram

```
┌─────────────────────────────────────────────────────┐
│                   USER / DASHBOARD                  │
│              POST /analyze  {user_request}          │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                      │
│  1. Validate user request                           │
│  2. Generate run_id                                 │
│  3. Initialise shared state                         │
│  4. Write pipeline_start audit log                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   MCP LAYER                         │
│  Execute all 5 MCPs (sequential within MCP layer)   │
│                                                     │
│  ├── Google Sheets MCP   → FAIL = HALT              │
│  ├── Calendar MCP        → FAIL = HALT              │
│  ├── News MCP            → FAIL = DEGRADE + CONTINUE│
│  ├── Supplier Intel MCP  → FAIL = HALT              │
│  └── Risk Registry MCP   → FAIL = DEGRADE + CONTINUE│
│                                                     │
│  Validate all responses                             │
│  Load into shared_state.mcp_data                    │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│            PARALLEL AGENT BLOCK                     │
│                                                     │
│   ┌──────────────┐  ┌──────────────┐               │
│   │  Inventory   │  │   Finance    │               │
│   │    Agent     │  │    Agent     │               │
│   └──────┬───────┘  └──────┬───────┘               │
│          │                 │                        │
│   ┌──────────────┐  ┌──────────────┐               │
│   │   Supplier   │  │  Compliance  │               │
│   │    Agent     │  │    Agent     │               │
│   └──────┬───────┘  └──────┬───────┘               │
│          │                 │                        │
│          └────────┬────────┘                        │
│    Wait for all 4 → aggregate into shared state     │
└───────────────────┬─────────────────────────────────┘
                        │
                        ▼
              ┌───────────────────┐
              │  Risk Tracker     │
              │     Agent         │
              └────────┬──────────┘
                       │
                       ▼
              ┌───────────────────┐
              │  Strategy Agent   │
              └────────┬──────────┘
                       │
                       ▼
              ┌───────────────────┐
              │ Communication     │
              │    Agent          │
              └────────┬──────────┘
                       │
          ┌────────────▼────────────┐
          │   HUMAN APPROVAL GATE   │
          │  Cache shared state.    │
          │  Return intermediate    │
          │  payload to dashboard.  │
          └────────────┬────────────┘
                       │
            (POST /analyze/approve)
                       │
                       ▼
              ┌───────────────────┐
              │  Evaluation Agent │
              └────────┬──────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│             DASHBOARD PAYLOAD ASSEMBLY              │
│  Assemble response from shared state                │
│  Write pipeline_complete audit log                  │
│  Return final dashboard payload                     │
└─────────────────────────────────────────────────────┘
```

### 6.2 Step-by-Step Execution Order

| Step | Action | Dependency | Endpoint / Trigger |
|---|---|---|---|
| 1 | Validate user request | None | `POST /analyze` |
| 2 | Generate `run_id` | Step 1 | `POST /analyze` |
| 3 | Initialise shared state | Step 2 | `POST /analyze` |
| 4 | Write `pipeline_start` audit log | Step 3 | `POST /analyze` |
| 5 | Execute Google Sheets MCP | Step 4 | `POST /analyze` |
| 6 | Execute Calendar MCP | Step 5 | `POST /analyze` |
| 7 | Execute News MCP | Step 5 | `POST /analyze` |
| 8 | Execute Supplier Intelligence MCP | Step 5 | `POST /analyze` |
| 9 | Execute Risk Registry MCP | Step 5 | `POST /analyze` |
| 10 | Validate and load all MCP data into shared state | Steps 5–9 | `POST /analyze` |
| 11 | Dispatch Inventory, Finance, Supplier, Compliance Agents in parallel | Step 10 | `POST /analyze` |
| 12 | Await all four parallel agents | Step 11 | `POST /analyze` |
| 13 | Dispatch Risk Tracker Agent | Step 12 | `POST /analyze` |
| 14 | Dispatch Strategy Agent | Step 13 | `POST /analyze` |
| 15 | Dispatch Communication Agent | Step 14 | `POST /analyze` |
| 16 | **Cache state; return `awaiting_human_approval` payload to UI** | Step 15 | `POST /analyze` (Completes) |
| 17 | Receive approval; retrieve cached state; write HITL audit log | Step 16 | `POST /analyze/approve` |
| 18 | Dispatch Evaluation Agent | Step 17 (approved) | `POST /analyze/approve` |
| 19 | Assemble final dashboard payload | Step 18 | `POST /analyze/approve` |
| 20 | Write `pipeline_complete` audit log | Step 19 | `POST /analyze/approve` |
| 21 | Return final dashboard payload to caller | Step 20 | `POST /analyze/approve` (Completes) |

---

## 7. MCP Orchestration Rules

### 7.1 Execution Timing

All five MCPs are executed in the MCP Layer **before any agent is dispatched**. No agent may be called until all MCP responses (success, degraded, or structured error) have been received and processed.

### 7.2 MCP Response Validation

Each MCP response is validated immediately upon receipt:
- The response envelope must match the Standard Success or Standard Error format defined in `API_CONTRACTS.md`.
- On success, the `data` field is validated against the MCP-specific output schema.
- Any response that does not conform to the envelope structure is treated as a `FETCH_FAILED` error.

### 7.3 How MCP Data Enters Shared State

After a successful MCP call, the Orchestrator maps the MCP `data` payload into the corresponding `shared_state.mcp_data` fields:

| MCP | Shared State Fields Populated | Status Field Populated |
|---|---|---|
| Google Sheets MCP | `inventory_data`, `sales_data`, `expenses_data`, `supplier_data` | `google_sheets_mcp_status` |
| Calendar MCP | `compliance_data` (calendar_events array) | `calendar_mcp_status` |
| News MCP | `supplier_news` | `news_mcp_status` |
| Supplier Intelligence MCP | `supplier_intelligence` | `supplier_intelligence_mcp_status` |
| Risk Registry MCP | `risk_history`, `risk_status`, `risk_trends` | `risk_registry_mcp_status` |

### 7.4 MCP Failure Handling

| MCP | On Failure | Behavior |
|---|---|---|
| Google Sheets MCP | **HALT PIPELINE** | Return structured error to dashboard; set `system_status: "error"`; set `google_sheets_mcp_status: "error"`; set remaining uncalled MCPs to `"skipped"`; write audit log |
| Calendar MCP | **HALT PIPELINE** | Return structured error to dashboard; set `system_status: "error"`; set `calendar_mcp_status: "error"`; set remaining uncalled MCPs to `"skipped"`; write audit log |
| Supplier Intelligence MCP | **HALT PIPELINE** | Return structured error to dashboard; set `system_status: "error"`; set `supplier_intelligence_mcp_status: "error"`; set remaining uncalled MCPs to `"skipped"`; write audit log |
| News MCP | **CONTINUE IN DEGRADED MODE** | Set `shared_state.mcp_data.news_mcp_status: "degraded"`; set `supplier_news: []`; write audit log (`mcp_call_degraded`); set `system_status: "degraded"` in final payload |
| Risk Registry MCP | **CONTINUE IN DEGRADED MODE** | Set `shared_state.mcp_data.risk_registry_mcp_status: "degraded"`; set `risk_history: []`, `risk_trends: []`; Risk Tracker Agent defaults `risk_trend` to `"stable"`; write audit log (`mcp_call_degraded`); set `system_status: "degraded"` in final payload |

---

## 8. Agent Execution Rules

### 8.1 Parallel Agents

The following four agents execute concurrently in a single parallel block:

- Inventory Agent
- Finance Agent
- Supplier Agent
- Compliance Agent

These agents have no dependencies on each other. They receive independent slices of MCP data from shared state. The Orchestrator must not dispatch any of these agents before the MCP Layer has completed.

### 8.2 Sequential Agents

The following agents execute sequentially, each dependent on the successful completion of the prior stage:

| Order | Agent | Depends On |
|---|---|---|
| 1 | Risk Tracker Agent | All four parallel agents |
| 2 | Strategy Agent | Risk Tracker Agent |
| 3 | Communication Agent | Strategy Agent |
| 4 | *(Human Approval Gate)* | Communication Agent output (`POST /analyze/approve`) |
| 5 | Evaluation Agent | Human Approval + Communication Agent |

### 8.3 Agent Input Dependencies

| Agent | Required Inputs From Shared State |
|---|---|
| Inventory Agent | `mcp_data.inventory_data`, `mcp_data.sales_data`, `products` (loaded from SQLite database during pipeline initialization), `business_type` |
| Finance Agent | `mcp_data.sales_data`, `mcp_data.expenses_data`, `period_days`, `business_type` |
| Supplier Agent | `mcp_data.supplier_data`, `mcp_data.supplier_intelligence`, `mcp_data.supplier_news`, `business_type` |
| Compliance Agent | `mcp_data.compliance_data`, `compliance_events` (from DB), `analysis_window_days`, `business_type` |
| Risk Tracker Agent | `agent_reports.inventory_risk_report`, `agent_reports.finance_risk_report`, `agent_reports.supplier_risk_report`, `agent_reports.compliance_risk_report`, `mcp_data.risk_history` |
| Strategy Agent | `agent_reports.business_risk_report`, `agent_reports.inventory_risk_report`, `agent_reports.finance_risk_report`, `agent_reports.supplier_risk_report`, `agent_reports.compliance_risk_report`, `business_type` |
| Communication Agent | `agent_reports.strategy_report`, `agent_reports.business_risk_report`, `business_name`, `recipient_name`, `communication_type` |
| Evaluation Agent | All seven preceding agent reports |

> [!NOTE]
> **Pipeline Initialization Sequence for Product Data**:
> 1. Load "products" from the local SQLite database.
> 2. Fetch inventory, suppliers, sales, and expenses from the Google Sheets MCP.
> 3. Populate shared state with both products (in `state["products"]`) and inventory (in `state["mcp_data"]["inventory_data"]`).
> 4. Pass both datasets to the Inventory Agent.

### 8.4 Timeout Policy

- Each agent call must complete within `AGENT_TIMEOUT_SECONDS` (loaded from `config.py`).
- If an agent does not return within the timeout window, the Orchestrator cancels the call, sets that agent's report to `null` in shared state, and returns `status: "error"` with `error_code: "AGENT_TIMEOUT"` for that agent.
- A timeout in any parallel agent halts the entire pipeline after the parallel block fails.
- A timeout in any sequential agent halts the pipeline at that stage.

### 8.5 Retry Policy

- On a transient agent failure (network error, non-business-logic exception), the Orchestrator retries up to `MAX_AGENT_RETRIES` times (loaded from `config.py`).
- Retries apply only to transient failures. A structured `status: "error"` response from an agent is a business-logic failure and is **not retried**.
- Each retry is logged to `audit_logs` with `event_type: "agent_retry"`.
- If all retries are exhausted, the pipeline halts with `error_code: "AGENT_MAX_RETRIES_EXCEEDED"`.

---

## 9. Guardrail Enforcement Rules

The Orchestrator is solely responsible for enforcing all four guardrails. Guardrail logic lives in `guardrails/` and is called by the Orchestrator — not by agents.

### 9.1 Human-In-The-Loop Approval

- **Trigger:** Communication Agent output is stored in shared state during `POST /analyze`.
- **Behavior:** The Orchestrator sets `guardrail_state.human_approval_status: "pending"` and `pipeline_status: "awaiting_human_approval"`. It caches the `shared_state` in active-run storage and returns the intermediate dashboard payload to the UI. The initial HTTP request completes. The dashboard renders the Communication Agent's `report_draft` and `email_draft` along with Approve and Reject controls.
- **On Approval (`POST /analyze/approve`):** The Orchestrator retrieves the cached `shared_state`, sets `human_approval_status: "approved"`, writes an audit log entry, dispatches the Evaluation Agent, and returns the final dashboard payload.
- **On Rejection (`POST /analyze/approve`):** The Orchestrator retrieves the cached `shared_state`, sets `human_approval_status: "rejected"`, sets `system_status: "error"`, logs the rejection to `audit_logs`, removes the cache, and returns the rejection payload to the dashboard.
- **This gate must never be bypassed under any circumstances.** Any code path that dispatches the Evaluation Agent without `human_approval_status: "approved"` is a critical guardrail violation.

### 9.2 Data Validation

- **Trigger:** Every MCP response before it is stored in shared state.
- **Enforced By:** `guardrails/data_validation.py`
- **Rules:**
  - Negative `current_stock` values are rejected; pipeline halts with `NEGATIVE_STOCK_VALUE`.
  - Missing required fields in any MCP response record are rejected with `MISSING_REQUIRED_FIELD`.
  - Invalid date strings are rejected with `INVALID_DATE_FORMAT`.
- **On Failure:** Halt the pipeline; return a structured error response.

### 9.3 Confidence Threshold

- **Trigger:** Evaluation Agent output is stored in shared state.
- **Rule:** If `evaluation_report.confidence_score` < 60, the Orchestrator sets `guardrail_state.confidence_threshold_passed: false` and `system_status: "human_review_required"` in the dashboard payload.
- **Behavior:** The dashboard payload is still assembled and returned, but `system_status` is set to `"human_review_required"` to signal that the results require human review before acting on them.
- **This is not an error state.** The pipeline completes successfully; results are surfaced; human review is flagged.

### 9.4 Audit Logging

- **Trigger:** Every MCP call, every agent dispatch, every agent completion, every guardrail event, and pipeline start/end/resume.
- **Behavior:** The Orchestrator calls the audit logging function in `guardrails/audit_logging.py` before every action and after every action.
- **Failures in audit logging must not silently pass.** If an audit log write fails, the Orchestrator logs the failure to stderr and appends the failure record to `execution_metadata.errors`, allowing the execution to continue non-blockingly while preserving visibility.

---

## 10. Error Handling Policy

All error responses from the Orchestrator follow the Standard Error Response envelope. Errors are classified into five categories.

### 10.1 Validation Errors

- **Source:** Invalid user request fields; failed data validation guardrail.
- **Behavior:** Return immediately without calling any MCP or agent.
- **Response:** `system_status: "error"`, `error_code: "VALIDATION_ERROR"`.
- **Escalation:** Log to `audit_logs`. No further escalation.

### 10.2 MCP Errors

- **Source:** MCP authentication failures, fetch failures, missing data.
- **Behavior:** Apply per-MCP policy from Section 7 (halt or degrade).
- **Response:** `system_status: "error"` on halt; `system_status: "degraded"` on degrade.
- **Escalation:** Log to `audit_logs`. Surface in dashboard `system_status`.

### 10.3 Agent Errors

- **Source:** Agent returns `status: "error"` with a structured error payload.
- **Behavior:** Halt pipeline at the failing agent. Retry if the failure is transient (up to `MAX_AGENT_RETRIES`).
- **Response:** `system_status: "error"`, `error_code` from the agent's error payload, `failed_agent` field identifying the agent.
- **Escalation:** Log to `audit_logs`. Surface in dashboard.

### 10.4 Unexpected Errors

- **Source:** Unhandled exceptions in Orchestrator code.
- **Behavior:** Catch with a top-level `try/except`. Do not allow exceptions to propagate to the API response.
- **Response:** `system_status: "error"`, `error_code: "UNEXPECTED_ERROR"`, `error_message` with exception detail.
- **Escalation:** Log full stack trace to `audit_logs` and to application stderr.

### 10.5 System Errors

- **Source:** Database write failures, shared state corruption, configuration load failures.
- **Behavior:** Halt pipeline immediately (except audit log write failures, which log to `execution_metadata.errors`).
- **Response:** `system_status: "error"`, `error_code: "SYSTEM_ERROR"`.
- **Escalation:** Log to stderr. If database is unavailable, log to a local fallback file. Alert on-call if configured.

### 10.6 Error Escalation Summary

| Error Category | Pipeline Action | Dashboard Status | Audit Log |
|---|---|---|---|
| Validation Error | Halt immediately | `error` | Yes |
| Critical MCP Error | Halt | `error` | Yes |
| Degraded MCP | Continue | `degraded` | Yes (`mcp_call_degraded`) |
| Agent Error | Halt at stage | `error` | Yes |
| Unexpected Error | Halt | `error` | Yes (with stack trace) |
| System Error | Halt immediately | `error` | Yes |

---

## 11. Audit Logging Requirements

All audit logs are written to the `audit_logs` table via the database helper layer in `database/`. Logs must be written by the Orchestrator — not by agents.

### 11.1 When Logs Are Written

A log entry is written:
- At pipeline start (before any MCP call).
- Before each MCP call.
- After each MCP call (success, error, or degraded).
- Before each agent dispatch.
- After each agent completes (success or error).
- At every guardrail enforcement event (validation rejection, HITL pause, HITL approval/rejection, confidence gate trigger).
- At pipeline completion (success, error, or degraded).
- On every retry attempt.

### 11.2 Required Fields

Every audit log entry must contain the following fields:

| Field | Type | Description |
|---|---|---|
| `log_id` | string | Unique log entry identifier (UUID) |
| `run_id` | string | Analysis run identifier; links all entries for a single run |
| `event_type` | string | Type of event (see 11.3) |
| `agent_name` | string or null | Name of the agent; null for MCP and pipeline events |
| `input_payload` | object or null | Serialized input passed to the agent or MCP; null for pipeline events |
| `output_payload` | object or null | Serialized output received; null if not yet available |
| `status` | string | `"success"`, `"error"`, `"retry"`, `"skipped"`, or `"degraded"` |
| `error_code` | string or null | Error code if `status` is `"error"` |
| `timestamp` | string | ISO 8601 timestamp of the event |

### 11.3 Event Type Values

| `event_type` | When Used |
|---|---|
| `pipeline_start` | Run begins |
| `pipeline_complete` | Run ends successfully |
| `pipeline_error` | Run ends with an error |
| `mcp_call_start` | Before each MCP call |
| `mcp_call_complete` | After each MCP call |
| `mcp_call_degraded` | MCP failed non-critically and entered degraded mode |
| `mcp_call_error` | MCP returned a critical error |
| `agent_dispatch` | Before each agent is called |
| `agent_complete` | After each agent returns |
| `agent_error` | Agent returned `status: "error"` |
| `agent_retry` | Retry attempt initiated |
| `guardrail_validation_failed` | Data validation guardrail triggered |
| `guardrail_hitl_pending` | Human approval gate activated; pipeline paused |
| `guardrail_hitl_approved` | Human approved the communication draft; pipeline resumed |
| `guardrail_hitl_rejected` | Human rejected the communication draft; pipeline halted |
| `guardrail_confidence_flagged` | Confidence score below threshold |

### 11.4 Example Log Entry

```json
{
  "log_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "run_id": "9f8e7d6c-5b4a-3210-fedc-ba9876543210",
  "event_type": "agent_complete",
  "agent_name": "inventory_agent",
  "input_payload": {
    "products": [ ],
    "inventory": [ ],
    "sales": [ ],
    "business_type": "retail"
  },
  "output_payload": {
    "agent": "inventory_agent",
    "inventory_risk_score": 72,
    "stockout_prediction": [ ],
    "reorder_recommendation": [ ],
    "status": "success",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "status": "success",
  "error_code": null,
  "timestamp": "2024-01-15T10:30:01Z"
}
```

---

## 12. Dashboard Response Contract

The Orchestrator assembles and returns this payload at the end of every completed pipeline run (and during the intermediate HITL pause). This is the single object consumed by the Streamlit dashboard.

### 12.1 Dashboard Payload Schema

```json
{
  "run_id": "string (UUID)",
  "system_status": "success | human_review_required | awaiting_human_approval | error | degraded",
  "business_name": "string",
  "business_type": "string",
  "generated_at": "string (ISO 8601)",

  "scores": {
    "business_health_score": "integer | null",
    "business_risk_score": "integer | null",
    "inventory_risk": "integer | null",
    "finance_risk": "integer | null",
    "supplier_risk": "integer | null",
    "compliance_risk": "integer | null",
    "confidence_score": "integer | null"
  },

  "top_recommendations": [
    {
      "rank": "integer",
      "action_title": "string",
      "action_description": "string",
      "target_domain": "inventory | finance | supplier | compliance",
      "urgency": "immediate | this_week | this_month",
      "expected_impact": "string"
    }
  ],

  "risk_trend": "improving | stable | deteriorating | null",
  "critical_risks": [ ],

  "communication_draft": {
    "report_draft": { },
    "email_draft": { },
    "approval_required": true,
    "approval_status": "pending | approved | rejected"
  },

  "evaluation": {
    "validation_status": "passed | passed_with_warnings | failed | null",
    "human_review_flag": "boolean | null",
    "warnings": [ ]
  },

  "mcp_status": {
    "google_sheets_mcp": "success | error | skipped",
    "calendar_mcp": "success | error | skipped",
    "news_mcp": "success | degraded | skipped",
    "supplier_intelligence_mcp": "success | error | skipped",
    "risk_registry_mcp": "success | degraded | skipped"
  },

  "execution_metadata": {
    "pipeline_duration_ms": "integer",
    "agent_execution_times_ms": { },
    "mcp_execution_times_ms": { },
    "errors": [ ]
  },

  "error": {
    "error_code": "string | null",
    "error_message": "string | null",
    "failed_agent": "string | null",
    "failed_mcp": "string | null"
  }
}
```

### 12.2 Field Notes

- All `scores` fields are `null` if the relevant agent did not complete successfully (e.g., during the HITL pause, `confidence_score` is `null`).
- `top_recommendations` is populated from `strategy_report.priority_1_action`, `priority_2_action`, and `priority_3_action`. It is an empty array if the Strategy Agent did not complete.
- `communication_draft` is included regardless of approval status, so the dashboard can render the approval gate.
- `execution_metadata.errors` preserves all non-fatal warnings (degraded MCPs, audit log failures) for UI inspection.
- `error` fields are all `null` on a successful run or during HITL pause.
- `execution_metadata.pipeline_duration_ms` is computed as the difference between `pipeline_complete` (or current pause time) and `pipeline_start` timestamps.

---

## 13. Non-Functional Requirements

### 13.1 Reliability
- The Orchestrator must handle MCP degraded modes without crashing.
- All error paths must return structured responses; unhandled exceptions must never reach the API consumer.
- Audit logs must be written before and after every action so that partial runs are recoverable.

### 13.2 Performance
- Parallel agent execution of the four core agents must be non-blocking; all four must execute concurrently.
- MCP calls should be made as close to concurrently as the MCP Layer allows (sequential within the MCP Layer block is acceptable in V1).
- The Orchestrator must not perform any business computation that delays agent dispatch.

### 13.3 Security
- All credentials are loaded from environment variables via `config.py`. No credentials appear in shared state, audit logs, or dashboard payloads.
- Input payloads passed to agents must not include raw API keys or secrets.
- The Human-In-The-Loop gate must be enforced in Orchestrator code, not left to the UI.

### 13.4 Scalability
- Shared state is scoped to a single run and must not bleed between concurrent runs.
- Each run must be independently identifiable via its `run_id`.
- The database helper layer must be the only path for writing to SQLite; the Orchestrator must not write raw SQL.

### 13.5 Maintainability
- All Orchestrator logic lives in `agents/orchestrator.py` (or `main.py` per the frozen folder structure).
- Guardrail logic is imported from `guardrails/`; it must not be inlined in the Orchestrator.
- Type hints are required on all Orchestrator function signatures.
- Docstrings are required on all public Orchestrator functions.

### 13.6 Observability
- `execution_metadata` must be populated and included in every dashboard response.
- Every MCP and agent execution time must be recorded in milliseconds.
- All errors, retries, and guardrail events must be discoverable via `audit_logs` queries filtered by `run_id`.

---

## 14. Success Criteria

A pipeline run is considered fully successful when all of the following conditions are met:

| # | Criterion | Verification |
|---|---|---|
| 1 | User request validated with no missing required fields | `validation_passed: true` before MCP calls |
| 2 | All five MCPs executed (critical MCPs returned success) | `mcp_status` shows `"success"` for Google Sheets, Calendar, and Supplier Intelligence MCPs |
| 3 | Shared state populated with all MCP data | All `mcp_data` fields non-null |
| 4 | All four parallel agents completed with `status: "success"` | `agent_reports.inventory_risk_report`, `finance_risk_report`, `supplier_risk_report`, `compliance_risk_report` all non-null |
| 5 | Risk Tracker Agent completed with `status: "success"` | `agent_reports.business_risk_report` non-null |
| 6 | Strategy Agent completed with `status: "success"` | `agent_reports.strategy_report` non-null with three priority actions |
| 7 | Communication Agent completed with `status: "success"` and `approval_required: true` | `agent_reports.communication_draft` non-null, `approval_status: "pending"` |
| 8 | Human approval received via `POST /analyze/approve` | `guardrail_state.human_approval_status: "approved"` |
| 9 | Evaluation Agent completed with `status: "success"` | `agent_reports.evaluation_report` non-null |
| 10 | Confidence score evaluated | `evaluation_report.confidence_score` successfully calculated |
| 11 | Dashboard payload assembled and returned | `system_status` is `"success"` (if confidence >= 60) or `"human_review_required"` (if confidence < 60) |
| 12 | All audit log entries written for every step | `audit_logs` contains complete run trace queryable by `run_id` |

---

## 15. Failure Conditions

The following conditions constitute Orchestrator failures. Each must halt or degrade the pipeline and return a structured response.

| # | Condition | Error Code | Pipeline Action |
|---|---|---|---|
| 1 | User request missing required fields | `VALIDATION_ERROR` | Halt before MCP layer |
| 2 | Google Sheets MCP unavailable or returns error | `MCP_GOOGLE_SHEETS_FAILED` | Halt; return error; set uncalled MCPs to skipped |
| 3 | Calendar MCP unavailable or returns error | `MCP_CALENDAR_FAILED` | Halt; return error; set uncalled MCPs to skipped |
| 4 | Supplier Intelligence MCP unavailable or returns error | `MCP_SUPPLIER_INTELLIGENCE_FAILED` | Halt; return error; set uncalled MCPs to skipped |
| 5 | Negative inventory stock value in MCP data | `NEGATIVE_STOCK_VALUE` | Halt; return validation error |
| 6 | Any parallel agent returns `status: "error"` | `PARALLEL_AGENT_FAILED` | Halt after parallel block |
| 7 | Any parallel agent exceeds timeout | `AGENT_TIMEOUT` | Halt after parallel block |
| 8 | Any parallel agent exhausts max retries | `AGENT_MAX_RETRIES_EXCEEDED` | Halt after parallel block |
| 9 | Risk Tracker Agent returns `status: "error"` | `RISK_TRACKER_FAILED` | Halt |
| 10 | Strategy Agent returns `status: "error"` | `STRATEGY_AGENT_FAILED` | Halt |
| 11 | Communication Agent returns `status: "error"` | `COMMUNICATION_AGENT_FAILED` | Halt |
| 12 | Human rejects communication draft | `HUMAN_APPROVAL_REJECTED` | Halt; return rejection status |
| 13 | Evaluation Agent returns `status: "error"` | `EVALUATION_AGENT_FAILED` | Halt |
| 14 | Shared state missing a required field when building agent inputs | `SHARED_STATE_CORRUPTION` | Halt; system error |
| 15 | Database write failure for audit log | `AUDIT_LOG_WRITE_FAILED` | Log to stderr; append to `execution_metadata.errors`; continue (non-blocking) |
| 16 | Configuration load failure (`config.py`) | `CONFIG_LOAD_FAILED` | Halt before MCP layer; system error |
| 17 | Unhandled exception in Orchestrator code | `UNEXPECTED_ERROR` | Halt; return error with stack trace in logs |
| 18 | Pipeline exceeds total wall-clock timeout | `PIPELINE_TIMEOUT` | Halt; cancel all pending tasks; return error |
| 19 | Evaluation Agent dispatched with `human_approval_status` not `"approved"` | `GUARDRAIL_VIOLATION` | **Critical violation; halt immediately; log as critical severity** |

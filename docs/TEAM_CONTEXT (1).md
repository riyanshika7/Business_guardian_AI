# TEAM_CONTEXT.md

> **Business Guardian AI — Team Context & Onboarding Reference v1.0**
> Read this before writing a single line of code.

---

## 1. Project Overview

**Project Name:** Business Guardian AI
**Category:** Multi-Agent Business Intelligence & Risk Management System
**Timeline:** 4-day hackathon build

**Goal:** Help small and medium businesses proactively monitor inventory, suppliers, finances, compliance obligations, and operational risks. The system uses a pipeline of specialized AI agents to deliver risk scores, strategy recommendations, and communication drafts — always with a human in the loop for consequential decisions.

You are joining as an **implementation engineer**. The architecture is designed and frozen. Your job is to implement assigned modules faithfully. Do not redesign. Do not improvise new patterns. Follow the contracts.

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Agent Framework | Google ADK |
| Backend API | FastAPI |
| Frontend Dashboard | Streamlit |
| Database | SQLite |
| Version Control | GitHub |
| Deployment | Cloud Run (or equivalent) |

---

## 3. Architecture Overview

The system follows a **sequential pipeline with a parallel core layer**:

```
User
  ↓
Orchestrator
  ↓
MCP Layer  (data fetched here before agents run)
  ↓
┌─────────────────────────────────────────────────┐
│  Inventory Agent  Finance Agent  Supplier Agent  Compliance Agent  │
│                    (Parallel Execution)                              │
└─────────────────────────────────────────────────┘
  ↓
Risk Tracker Agent
  ↓
Strategy Agent
  ↓
Communication Agent  ← HUMAN APPROVAL GATE
  ↓
Evaluation Agent
  ↓
Dashboard
```

**Key rules:**
- The four core agents (Inventory, Finance, Supplier, Compliance) run **in parallel**.
- All other agents run **sequentially** after the parallel block.
- Every inter-agent message is **structured JSON**. No free-form text.
- The Communication Agent must **never** send communications without human approval.

---

## 4. Agents

There are **eight agents** in the system. Each agent has a single responsibility and produces a defined JSON output. Do not add agents. Do not merge agents. Do not expand agent responsibilities.

| Agent | Responsibility | Key Output |
|---|---|---|
| Inventory Agent | Analyze stock levels, predict stockouts | `inventory_risk_score`, `stockout_prediction`, `reorder_recommendation` |
| Finance Agent | Analyze revenue, expenses, profitability | `finance_risk_score`, `profit_margin`, `financial_recommendation` |
| Supplier Agent | Monitor supplier dependency and risk | `supplier_risk_score`, `dependency_score`, `supplier_recommendation` |
| Compliance Agent | Track compliance deadlines and obligations | `compliance_risk_score`, `deadline_alerts`, `compliance_recommendation` |
| Risk Tracker Agent | Aggregate all four risk scores | `business_risk_score` |
| Strategy Agent | Convert risk into prioritized actions | `priority_1_action`, `priority_2_action`, `priority_3_action`, `business_health_score` |
| Communication Agent | Draft reports and emails (human-approved only) | `report_draft`, `email_draft` |
| Evaluation Agent | Validate all outputs, flag uncertainty | `confidence_score`, `validation_status`, `human_review_flag` |

Full input/output schemas and success criteria are defined in `AGENT_CONTRACTS.md`.

---

## 5. Skills

Skills are **business rule modules**, not agents. They contain domain logic that agents call. Skills do not have their own input/output pipeline — they are helper libraries.

| Skill | Status | Purpose |
|---|---|---|
| Retail Skill | Required | Retail-specific inventory and margin rules |
| Business Health Skill | Required | Business health scoring logic |
| Forecasting Skill | Required | Demand and risk forecasting calculations |
| Agriculture Skill | Optional | Agriculture-sector business rules |
| E-Commerce Skill | Optional | E-commerce-specific risk and sales logic |

Skills live in `skills/` and are imported by agents as needed. A skill is a Python module, not an ADK agent.

---

## 6. MCP Layer

The MCP layer provides all external data to the agents. Data is fetched via MCP integrations **before** the agent pipeline begins. Agents receive MCP data as structured input — they do not call MCPs directly.

| MCP | Data Provided |
|---|---|
| Google Sheets MCP | Inventory data, sales data, expense data, supplier data |
| Calendar MCP | Compliance events, renewal dates |
| News MCP | Supplier news, industry news |
| Supplier Intelligence MCP | Supplier profile, supplier history, supplier risk data |
| Risk Registry MCP | Risk history, risk status, risk scores, risk trends |

Full input/output schemas and error formats are defined in `API_CONTRACTS.md`.

---

## 7. Database

The database is **SQLite**. There are exactly **nine approved tables**:

| Table | Contains |
|---|---|
| `products` | Product catalog entries |
| `inventory` | Inventory level records |
| `sales` | Sales transactions |
| `expenses` | Business expense records |
| `suppliers` | Supplier profiles |
| `compliance_events` | Compliance deadlines and obligations |
| `risk_scores` | Historical risk scores by agent |
| `reports` | Generated report content |
| `audit_logs` | Full audit trail of all agent actions |

**Do not create new tables.** All database access goes through the helper layer in `database/`. All schemas are defined in `DATA_MODELS.md`.

---

## 8. Workflow

A complete analysis run follows this sequence:

1. **User triggers analysis** via the Streamlit dashboard or FastAPI endpoint.
2. **Orchestrator** receives the request and coordinates the pipeline.
3. **MCP Layer** fetches fresh data from all connected sources (Google Sheets, Calendar, News, Supplier Intelligence, Risk Registry).
4. **Core agents run in parallel:** Inventory Agent, Finance Agent, Supplier Agent, and Compliance Agent each analyze their domain and return a structured risk report.
5. **Risk Tracker Agent** consumes the four risk reports and produces a unified Business Risk Score.
6. **Strategy Agent** consumes the Business Risk Score and produces three prioritized action recommendations and a Business Health Score.
7. **Communication Agent** drafts a report and email summary. **Execution pauses here.** The dashboard displays the draft and requires explicit human approval before any communication is finalized.
8. **Evaluation Agent** validates all outputs, assigns a confidence score, and flags any results that fall below the 60% confidence threshold for human review.
9. **Dashboard** displays the full analysis, scores, recommendations, draft communications, and evaluation results.
10. **Audit logs** are written at every agent step.

---

## 9. Guardrails

Four guardrails are active at all times:

### 9.1 Human-In-The-Loop Approval
- **Trigger:** Communication Agent output or any supplier action.
- **Behavior:** Pipeline pauses; human must explicitly approve before proceeding.
- **Never bypass this gate.**

### 9.2 Data Validation
- **Trigger:** Any incoming data before agent processing.
- **Rejects:** Missing required fields, negative inventory values, invalid date formats.
- **Response:** Structured validation error JSON.

### 9.3 Confidence Threshold
- **Trigger:** Evaluation Agent produces a confidence score below 60.
- **Behavior:** Output status is set to `"human_review_required"`. Any communication drafts or supplier actions associated with the analysis require explicit human review and approval before proceeding.

### 9.4 Audit Logging
- **Trigger:** Every agent action.
- **Stores:** Agent name, input payload, output payload, timestamp (ISO 8601).
- **Table:** `audit_logs`

### 9.5 Timeout Handling

- **Trigger:** An MCP request or agent execution exceeds the configured timeout period.
- **Behavior:** The operation returns a structured timeout error JSON.
- The Orchestrator records the timeout event in `audit_logs`.
- Timeout values are defined in `config.py`.

### 9.6 MCP Failure Handling

- **Trigger:** An MCP source is unavailable, returns invalid data, or fails during execution.
- **Behavior:** A structured error response is generated identifying the failed MCP.
- The Orchestrator records the failure in `audit_logs`.
- Partial execution behavior is governed by `API_CONTRACTS.md`.

All guardrail logic lives in `guardrails/`.

---

## 10. Development Rules

- **Never** change the architecture, folder structure, agent responsibilities, database tables, data models, or contracts.
- **Only** implement your assigned module.
- **All** agent outputs must be structured JSON matching the schemas in `AGENT_CONTRACTS.md`.
- **All** database access must go through the `database/` helper layer.
- **All** secrets and configuration must be loaded from `.env` via `config.py`.
- **All** agent actions must be written to `audit_logs` before the function returns.
- Write at least one unit test for every agent you implement.
- Use type hints on all function signatures.
- Use `black` for code formatting before committing.

---

## 11. AI Assistant Usage Rules

If you use an AI coding assistant (including Claude) to help implement modules:

- Always provide the relevant contracts from `AGENT_CONTRACTS.md`, `DATA_MODELS.md`, and `API_CONTRACTS.md` as context.
- Always provide this `TEAM_CONTEXT.md` and `PROJECT_CONSTITUTION.md` as system context.
- Never ask an AI assistant to redesign the architecture.
- Never accept AI-generated code that adds new agents, new tables, new folders, or changes existing schemas.
- Always review AI-generated code against the frozen contracts before committing.
- If the AI suggests an "improvement" that deviates from the architecture, reject it.

---

## 12. Output Requirements

- All inter-agent outputs: **structured JSON only**.
- All API responses: use the standard success/error response envelopes defined in `API_CONTRACTS.md`.
- Dashboard: must display risk scores, recommendations, draft communications, confidence scores, and human approval controls.
- Audit logs: must be written for every agent action without exception.
- Reports: must be storable in the `reports` table and retrievable via the FastAPI backend.
# PROJECT_CONSTITUTION.md

> **Business Guardian AI — Governing Constitution v1.0**
> Hackathon Edition | Status: FROZEN

---

## 1. Mission

Business Guardian AI exists to help small and medium businesses proactively monitor inventory, suppliers, finances, compliance obligations, and operational risks through a structured multi-agent intelligence system that delivers actionable recommendations while keeping humans in control of all consequential decisions.

---

## 2. Scope

### 2.1 In Scope (V1)

- Inventory monitoring and stockout prediction
- Supplier risk monitoring and dependency scoring
- Finance analysis including revenue, expenses, and profitability
- Compliance deadline tracking and obligation monitoring
- Business risk aggregation and scoring
- Strategy recommendation generation
- Communication drafting with human approval gate
- Evaluation and confidence scoring of all agent outputs
- Dashboard visualization for business owners
- Audit logging of all agent actions
- Human-in-the-loop approval for external communications and supplier actions

### 2.2 Out of Scope (V1)

The following are explicitly excluded and must not be implemented:

- SAP or ERP integrations
- Banking API connections
- Automated purchasing workflows
- Autonomous email sending (any email must be human-approved)
- Payment systems of any kind
- Additional database tables not listed in the approved schema
- Alternative agent architectures
- Free-form inter-agent communication (all outputs must be structured JSON)

---

## 3. Architecture Principles

1. **Sequential with Parallel Core** — The Orchestrator dispatches Inventory, Finance, Supplier, and Compliance agents in parallel. All subsequent agents execute sequentially.
2. **Structured Outputs Only** — Every agent must return structured JSON. No free-form text between agents.
3. **Human Control at Boundaries** — No external communication or supplier action may occur without explicit human approval.
4. **Confidence Gating** — Any output with a confidence score below 60 must be flagged for human review and must not proceed automatically.
5. **Audit Everything** — Every agent action, input, and output must be logged to the `audit_logs` table with a timestamp.
6. **Fail Safe** — On data validation failure, reject the input and return a structured error. Never silently proceed with invalid data.
7. **Minimal Footprint** — The system uses only approved database tables and only the defined folder structure. No scope creep.
8. **Skill Separation** — Business rules live in Skills, not in Agents. Agents orchestrate; Skills compute.

---

## 4. Folder Structure Policy

The following folder structure is **frozen** and must not be modified:

```
business_guardian_ai/
├── agents/          # Agent implementations only
├── skills/          # Business rule modules (not agents)
├── mcp/             # MCP server integrations
├── models/          # Pydantic data models and JSON schemas
├── guardrails/      # Validation, confidence, HITL, audit logic
├── database/        # SQLite setup, migrations, query helpers
├── ui/              # Streamlit dashboard
├── docs/            # All governance documents
├── tests/           # Unit and integration tests
├── main.py          # Application entrypoint
└── config.py        # Environment and configuration constants
```

**Rules:**

- Do not create top-level folders outside this structure.
- Do not add subfolders without team approval.
- Each agent lives in `agents/` as a single Python file named `{agent_name}_agent.py`.
- Each skill lives in `skills/` as a single Python file named `{skill_name}_skill.py`.
- Each MCP integration lives in `mcp/` as a single Python file named `{mcp_name}_mcp.py`.

---

## 5. Database Policy

### 5.1 Approved Tables

The following nine tables are the only permitted database tables in V1:

| Table | Purpose |
|---|---|
| `products` | Product catalog |
| `inventory` | Current inventory records |
| `sales` | Sales transaction records |
| `expenses` | Expense records |
| `suppliers` | Supplier records |
| `compliance_events` | Compliance deadlines and obligations |
| `risk_scores` | Stored risk scores by agent and date |
| `reports` | Generated report storage |
| `audit_logs` | Agent action audit trail |

### 5.2 Database Rules

- No new tables may be created without explicit team approval and constitution amendment.
- All tables must use SQLite-compatible data types.
- All tables must include a primary key field.
- All timestamps must be stored as ISO 8601 strings.
- No raw SQL strings in agent code; use the database helper layer in `database/`.

---

## 6. Coding Standards

- **Language:** Python 3.10+
- **Framework:** Google ADK for all agent definitions
- **Backend:** FastAPI for all API endpoints
- **Frontend:** Streamlit for the dashboard
- **Style:** PEP 8 compliant; use `black` for formatting
- **Type Hints:** Required on all function signatures
- **Docstrings:** Required on all public functions and classes
- **Imports:** Absolute imports only; no wildcard imports
- **Environment Variables:** All secrets and config values must live in `.env` and be loaded via `config.py`. Never hardcode credentials.
- **Error Handling:** All functions that call external services or database must use try/except with structured error returns.
- **Testing:** Every agent must have at least one unit test in `tests/`.

---

## 7. Security Standards

1. **No Hardcoded Credentials** — All API keys, database paths, and secrets must be loaded from environment variables.
2. **Human-In-The-Loop Enforcement** — The Communication Agent and any supplier action must pause and await explicit human approval before proceeding. This gate must never be bypassed.
3. **Data Validation at Entry** — All incoming data must pass validation before being processed by any agent. Reject invalid data with a structured error response.
4. **Confidence Threshold Enforcement** — Outputs with confidence < 60 must return `"status": "human_review_required"` and must not trigger downstream agents automatically.
5. **Audit Logging** — Every agent action must be written to `audit_logs` before the function returns.
6. **Input Sanitization** — Reject negative inventory values, missing required fields, and invalid date formats before processing.
7. **No Autonomous External Actions** — The system must never autonomously send emails, place orders, or contact suppliers.

---

## 8. Governance Rules

1. The architecture described in this document is the single source of truth.
2. No team member may unilaterally change agent responsibilities, data models, or folder structure.
3. All agent output schemas defined in `AGENT_CONTRACTS.md` are binding.
4. All data models defined in `DATA_MODELS.md` are binding.
5. All MCP contracts defined in `API_CONTRACTS.md` are binding.
6. Implementation engineers follow the architecture; they do not redesign it.
7. If a requirement cannot be met within the frozen architecture, it must be escalated — not worked around.
8. Deviations discovered during code review must be reverted, not rationalized.

---

## 9. Change Management Rules

1. **No unilateral changes.** All changes to architecture, schemas, folder structure, or database tables require team consensus and a constitution amendment.
2. **Document first.** Any approved change must be reflected in the relevant governance document before code is written.
3. **Version the change.** All governance documents carry a version number. Changes increment the version.
4. **Hackathon exception.** Given the 4-day timeline, changes must be approved by the project lead verbally and documented within 30 minutes.
5. **Backward compatibility.** Schema changes must not break existing agent contracts without explicit re-versioning of affected contracts.
6. **No scope creep.** Features listed under Out of Scope may not be added under any framing without a full scope review.

# AGENT_CONTRACTS.md

> **Business Guardian AI — Agent Contracts v1.0**
> All schemas in this document are binding. Do not modify without team approval and constitution amendment.

---

## Contract Structure

Every agent contract defines:
- **Purpose** — Single-sentence mission
- **Inputs** — What the agent receives
- **Outputs** — What the agent must return
- **JSON Output Schema** — Exact structure of the output
- **Success Criteria** — Conditions that define a valid run
- **Failure Conditions** — Conditions that must trigger an error response

---

## 1. Inventory Agent

### Purpose
Analyze current inventory levels, predict stockout risk, and recommend reorder actions.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `products` | array | Yes | List of product records from `products` table |
| `inventory` | array | Yes | List of inventory records from `inventory` table |
| `sales` | array | Yes | Recent sales records to calculate velocity |
| `business_type` | string | Yes | Business type for skill selection (e.g., `"retail"`, `"agriculture"`) |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"inventory_agent"` |
| `inventory_risk_score` | integer | Risk score 0–100 (higher = more risk) |
| `stockout_prediction` | array | List of products predicted to stock out |
| `reorder_recommendation` | array | List of products with recommended reorder quantities |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "inventory_agent",
  "inventory_risk_score": 72,
  "stockout_prediction": [
    {
      "product_id": "string",
      "product_name": "string",
      "current_stock": 45,
      "days_until_stockout": 14
    }
  ],
  "reorder_recommendation": [
    {
      "product_id": "string",
      "product_name": "string",
      "recommended_reorder_qty": 100,
      "reason": "string"
    }
  ],
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `inventory_risk_score` is an integer between 0 and 100.
- `stockout_prediction` is a list (may be empty).
- `reorder_recommendation` is a list (may be empty).
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- Input `inventory` array is empty or missing → return `status: "error"`, `error_code: "MISSING_INVENTORY_DATA"`.
- Any product has negative stock value → return `status: "error"`, `error_code: "INVALID_INVENTORY_VALUE"`.
- Required fields missing from any product or inventory record → return `status: "error"`, `error_code: "VALIDATION_FAILED"`.

---

## 2. Finance Agent

### Purpose
Analyze revenue, expenses, and profitability to assess financial health and risk.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `sales` | array | Yes | Sales records for the analysis period |
| `expenses` | array | Yes | Expense records for the analysis period |
| `period_days` | integer | Yes | Number of days in the analysis period |
| `business_type` | string | Yes | Business type for skill selection |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"finance_agent"` |
| `finance_risk_score` | integer | Risk score 0–100 (higher = more risk) |
| `profit_margin` | float | Profit margin as a percentage |
| `total_revenue` | float | Total revenue for the period |
| `total_expenses` | float | Total expenses for the period |
| `net_profit` | float | Net profit for the period |
| `financial_recommendation` | string | Actionable recommendation text |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "finance_agent",
  "finance_risk_score": 45,
  "profit_margin": 18.5,
  "total_revenue": 125000.00,
  "total_expenses": 101875.00,
  "net_profit": 23125.00,
  "financial_recommendation": "string",
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `finance_risk_score` is an integer between 0 and 100.
- `profit_margin` is a float (may be negative).
- `financial_recommendation` is a non-empty string.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- `sales` or `expenses` array is empty or missing → return `status: "error"`, `error_code: "MISSING_FINANCIAL_DATA"`.
- `period_days` is zero or negative → return `status: "error"`, `error_code: "INVALID_PERIOD"`.
- Any sales or expense record is missing required fields → return `status: "error"`, `error_code: "VALIDATION_FAILED"`.

---

## 3. Supplier Agent

### Purpose
Monitor supplier dependency levels and assess supplier relationship risk.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `suppliers` | array | Yes | Supplier records from `suppliers` table |
| `supplier_intelligence` | object | Yes | Enriched supplier data object from Supplier Intelligence MCP |
| `supplier_news` | array | No | Recent news items about suppliers |
| `business_type` | string | Yes | Business type for skill selection |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"supplier_agent"` |
| `supplier_risk_score` | integer | Aggregate supplier risk score 0–100 |
| `dependency_score` | integer | Supplier dependency score 0–100 |
| `high_risk_suppliers` | array | List of suppliers flagged as high risk |
| `supplier_recommendation` | string | Actionable recommendation text |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "supplier_agent",
  "supplier_risk_score": 60,
  "dependency_score": 75,
  "high_risk_suppliers": [
    {
      "supplier_id": "string",
      "supplier_name": "string",
      "risk_reason": "string",
      "risk_level": "high | medium | low"
    }
  ],
  "supplier_recommendation": "string",
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `supplier_risk_score` and `dependency_score` are integers between 0 and 100.
- `high_risk_suppliers` is a list (may be empty).
- `supplier_recommendation` is a non-empty string.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- `suppliers` array is empty or missing → return `status: "error"`, `error_code: "MISSING_SUPPLIER_DATA"`.
- `supplier_intelligence` object is missing → return `status: "error"`, `error_code: "MISSING_INTELLIGENCE_DATA"`.
- Any supplier record is missing required fields → return `status: "error"`, `error_code: "VALIDATION_FAILED"`.

---

## 4. Compliance Agent

### Purpose
Track compliance deadlines, regulatory obligations, and renewal dates to prevent lapses.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `compliance_events` | array | Yes | Compliance event records from `compliance_events` table |
| `calendar_events` | array | Yes | Upcoming events from Calendar MCP |
| `analysis_window_days` | integer | Yes | Number of days ahead to analyze |
| `business_type` | string | Yes | Business type for skill selection |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"compliance_agent"` |
| `compliance_risk_score` | integer | Risk score 0–100 (higher = more risk) |
| `deadline_alerts` | array | List of upcoming or overdue compliance items |
| `compliance_recommendation` | string | Actionable recommendation text |
| `overdue_count` | integer | Number of overdue compliance items |
| `due_soon_count` | integer | Number of items due within the analysis window |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "compliance_agent",
  "compliance_risk_score": 55,
  "deadline_alerts": [
    {
      "event_id": "string",
      "event_name": "string",
      "due_date": "string (ISO 8601 date)",
      "days_remaining": 5,
      "status": "overdue | due_soon | upcoming",
      "severity": "critical | high | medium | low"
    }
  ],
  "compliance_recommendation": "string",
  "overdue_count": 1,
  "due_soon_count": 3,
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `compliance_risk_score` is an integer between 0 and 100.
- `deadline_alerts` is a list (may be empty).
- `compliance_recommendation` is a non-empty string.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- `compliance_events` array is missing → return `status: "error"`, `error_code: "MISSING_COMPLIANCE_DATA"`.
- Any event has an invalid date format → return `status: "error"`, `error_code: "INVALID_DATE_FORMAT"`.
- `analysis_window_days` is zero or negative → return `status: "error"`, `error_code: "INVALID_ANALYSIS_WINDOW"`.

---

## 5. Risk Tracker Agent

### Purpose
Aggregate the four domain risk scores into a unified Business Risk Score.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `inventory_risk_report` | object | Yes | Full output from Inventory Agent |
| `finance_risk_report` | object | Yes | Full output from Finance Agent |
| `supplier_risk_report` | object | Yes | Full output from Supplier Agent |
| `compliance_risk_report` | object | Yes | Full output from Compliance Agent |
| `risk_history` | array | No | Historical risk scores from Risk Registry MCP |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"risk_tracker_agent"` |
| `business_risk_score` | integer | Aggregate risk score 0–100 |
| `risk_breakdown` | object | Weighted contribution of each domain risk |
| `risk_trend` | string | `"improving"`, `"stable"`, or `"deteriorating"` |
| `critical_risks` | array | List of risk areas scoring above 70 |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "risk_tracker_agent",
  "business_risk_score": 63,
  "risk_breakdown": {
    "inventory_risk_score": 72,
    "finance_risk_score": 45,
    "supplier_risk_score": 60,
    "compliance_risk_score": 55
  },
  "risk_trend": "stable",
  "critical_risks": [
    {
      "domain": "string",
      "score": 72,
      "severity": "critical | high | medium"
    }
  ],
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `business_risk_score` is an integer between 0 and 100.
- `risk_breakdown` contains all four domain scores.
- `risk_trend` is one of the three permitted values.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- Any of the four domain risk reports is missing → return `status: "error"`, `error_code: "MISSING_DOMAIN_REPORT"`.
- Any domain risk report has `status: "error"` → return `status: "error"`, `error_code: "UPSTREAM_AGENT_FAILED"`.
- Any domain risk score is outside 0–100 → return `status: "error"`, `error_code: "INVALID_RISK_SCORE"`.

---

## 6. Strategy Agent

### Purpose
Convert the aggregated business risk analysis into three prioritized action recommendations and a Business Health Score.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `business_risk_report` | object | Yes | Full output from Risk Tracker Agent |
| `inventory_risk_report` | object | Yes | Full output from Inventory Agent |
| `finance_risk_report` | object | Yes | Full output from Finance Agent |
| `supplier_risk_report` | object | Yes | Full output from Supplier Agent |
| `compliance_risk_report` | object | Yes | Full output from Compliance Agent |
| `business_type` | string | Yes | Business type for skill selection |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"strategy_agent"` |
| `business_health_score` | integer | Overall business health score 0–100 (higher = healthier) |
| `priority_1_action` | object | Highest priority recommended action |
| `priority_2_action` | object | Second priority recommended action |
| `priority_3_action` | object | Third priority recommended action |
| `rationale` | string | Brief explanation of prioritization logic |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "strategy_agent",
  "business_health_score": 48,
  "priority_1_action": {
    "action_title": "string",
    "action_description": "string",
    "target_domain": "inventory | finance | supplier | compliance",
    "urgency": "immediate | this_week | this_month",
    "expected_impact": "string"
  },
  "priority_2_action": {
    "action_title": "string",
    "action_description": "string",
    "target_domain": "inventory | finance | supplier | compliance",
    "urgency": "immediate | this_week | this_month",
    "expected_impact": "string"
  },
  "priority_3_action": {
    "action_title": "string",
    "action_description": "string",
    "target_domain": "inventory | finance | supplier | compliance",
    "urgency": "immediate | this_week | this_month",
    "expected_impact": "string"
  },
  "rationale": "string",
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `business_health_score` is an integer between 0 and 100.
- All three priority action objects are present and fully populated.
- `urgency` in each action is one of the three permitted values.
- `target_domain` in each action is one of the four permitted values.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- `business_risk_report` is missing or has `status: "error"` → return `status: "error"`, `error_code: "MISSING_RISK_REPORT"`.
- Any domain report required as input is missing → return `status: "error"`, `error_code: "MISSING_DOMAIN_REPORT"`.
- Cannot produce three distinct actions → return `status: "error"`, `error_code: "STRATEGY_GENERATION_FAILED"`.

---

## 7. Communication Agent

### Purpose
Generate a structured business report and an email draft summarizing the analysis and recommended actions. **Must never send communications automatically. Human approval is required before any output is used externally.**

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `strategy_report` | object | Yes | Full output from Strategy Agent |
| `business_risk_report` | object | Yes | Full output from Risk Tracker Agent |
| `business_name` | string | Yes | Name of the business for personalization |
| `recipient_name` | string | No | Name of the intended email recipient |
| `communication_type` | string | Yes | `"report"`, `"email"`, or `"both"` |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"communication_agent"` |
| `report_draft` | object or null | Structured report draft (null if not requested) |
| `email_draft` | object or null | Structured email draft (null if not requested) |
| `approval_required` | boolean | Always `true` |
| `approval_status` | string | Always `"pending"` on initial output |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "communication_agent",
  "report_draft": {
    "title": "string",
    "executive_summary": "string",
    "risk_summary": "string",
    "recommended_actions": ["string", "string", "string"],
    "business_health_score": 48,
    "generated_at": "string (ISO 8601)"
  },
  "email_draft": {
    "subject": "string",
    "recipient_name": "string",
    "body": "string",
    "generated_at": "string (ISO 8601)"
  },
  "approval_required": true,
  "approval_status": "pending",
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `approval_required` is always `true`.
- `approval_status` is always `"pending"` on initial output.
- At least one of `report_draft` or `email_draft` is non-null.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.
- No external communication has occurred.

### Failure Conditions
- `strategy_report` is missing or has `status: "error"` → return `status: "error"`, `error_code: "MISSING_STRATEGY_REPORT"`.
- `business_name` is missing or empty → return `status: "error"`, `error_code: "MISSING_BUSINESS_NAME"`.
- `communication_type` is not one of the permitted values → return `status: "error"`, `error_code: "INVALID_COMMUNICATION_TYPE"`.
- Any code path that sends communication without approval → return `status: "error"`, `error_code: "AUTONOMOUS_SEND_VIOLATION"`. **Critical violation; must never occur.**

---

## 8. Evaluation Agent

### Purpose
Validate all agent outputs, assign a confidence score to the full analysis pipeline, and flag results that require human review.

### Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `inventory_risk_report` | object | Yes | Full output from Inventory Agent |
| `finance_risk_report` | object | Yes | Full output from Finance Agent |
| `supplier_risk_report` | object | Yes | Full output from Supplier Agent |
| `compliance_risk_report` | object | Yes | Full output from Compliance Agent |
| `business_risk_report` | object | Yes | Full output from Risk Tracker Agent |
| `strategy_report` | object | Yes | Full output from Strategy Agent |
| `communication_draft` | object | Yes | Full output from Communication Agent |

### Outputs

| Field | Type | Description |
|---|---|---|
| `agent` | string | Always `"evaluation_agent"` |
| `confidence_score` | integer | Overall pipeline confidence score 0–100 |
| `validation_status` | string | `"passed"`, `"passed_with_warnings"`, or `"failed"` |
| `human_review_flag` | boolean | `true` if confidence < 60 or any validation failure |
| `validation_details` | array | Per-agent validation results |
| `warnings` | array | List of non-blocking warnings found |
| `status` | string | `"success"` or `"error"` |
| `timestamp` | string | ISO 8601 timestamp |

### JSON Output Schema

```json
{
  "agent": "evaluation_agent",
  "confidence_score": 74,
  "validation_status": "passed_with_warnings",
  "human_review_flag": false,
  "validation_details": [
    {
      "agent_name": "string",
      "validation_passed": true,
      "issues_found": ["string"]
    }
  ],
  "warnings": [
    {
      "warning_code": "string",
      "warning_message": "string",
      "affected_agent": "string"
    }
  ],
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Success Criteria
- `confidence_score` is an integer between 0 and 100.
- `validation_status` is one of the three permitted values.
- `human_review_flag` is `true` when `confidence_score` < 60 (independently of `validation_status`).
- `human_review_flag` is `true` when `validation_status` is `"failed"` (independently of `confidence_score`).
- `validation_details` contains one entry per evaluated agent.
- `status` is `"success"`.
- Audit log entry is written by the Orchestrator on behalf of this agent.

### Failure Conditions
- Any required upstream report is missing → return `status: "error"`, `error_code: "MISSING_UPSTREAM_REPORT"`.
- Unable to compute confidence score → return `status: "error"`, `error_code: "EVALUATION_FAILED"`.
- `confidence_score` computed as below 60 → set `human_review_flag: true`. `validation_status` remains as computed by validation logic (e.g., `"passed_with_warnings"` if validation passed but confidence is low). This is not an error condition; it is a valid outcome.

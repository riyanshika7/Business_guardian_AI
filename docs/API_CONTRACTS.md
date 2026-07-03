# API_CONTRACTS.md (v1.1 — Production-Grade Corrected Edition)

> **Business Guardian AI — MCP API Contracts v1.1**
> All schemas in this document are binding. Do not modify input schemas, output schemas, or error formats without team approval and constitution amendment.

---

## Overview

The Model Context Protocol (MCP) Layer sits between the Orchestrator and the external business data sources. All five MCP integrations are executed **before** any analytical agent is dispatched. Agents receive MCP data as structured JSON input — agents never invoke MCPs directly.

Every MCP integration must:
- Return a **Standard Success Response** envelope on successful data retrieval.
- Return a **Standard Error Response** envelope on failure.
- Validate all input parameters and reject requests with missing or invalid fields before initiating any external network or API calls.
- Never expose raw API credentials, tokens, or connection strings in any response payload or log trace.

---

## Standard Response Envelopes

### Standard Success Response

All MCP integrations wrap their retrieved output in this binding envelope.

```json
{
  "mcp": "string",
  "status": "success",
  "data": { },
  "warnings": ["string"] | null,
  "fetched_at": "string (ISO 8601 UTC timestamp)"
}
```

| Field | Type | Description |
|---|---|---|
| `mcp` | string | Identifier of the MCP producing this response (e.g., `"google_sheets_mcp"`) |
| `status` | string | Always `"success"` |
| `data` | object | MCP-specific payload containing requested records; see individual contracts below |
| `warnings` | array of strings or null | Non-fatal advisory messages (e.g., missing requested IDs that did not halt execution) |
| `fetched_at` | string | ISO 8601 UTC timestamp (format: `YYYY-MM-DDTHH:MM:SSZ`) when data was retrieved |

---

### Standard Error Response

All MCP integrations return this envelope on any failure or validation rejection.

```json
{
  "mcp": "string",
  "status": "error",
  "error_code": "string",
  "error_message": "string",
  "fetched_at": "string (ISO 8601 UTC timestamp)"
}
```

| Field | Type | Description |
|---|---|---|
| `mcp` | string | Identifier of the MCP producing this error |
| `status` | string | Always `"error"` |
| `error_code` | string | Machine-readable error code (see per-MCP specification tables below) |
| `error_message` | string | Clear, human-readable description of the failure cause |
| `fetched_at` | string | ISO 8601 UTC timestamp (format: `YYYY-MM-DDTHH:MM:SSZ`) when the failure occurred |

---

## Security Requirements

The following security mandates apply to all MCP integrations without exception:

1. **No Hardcoded Credentials.** All API keys, OAuth tokens, spreadsheet IDs, calendar IDs, and database connection strings must be loaded from environment variables via `config.py`. Never embed secrets in source code or return them in payloads.
2. **Pre-Flight Input Validation.** All required input fields, date ranges, and ID lists must be validated prior to initiating external network requests. Return a Standard Error Response immediately upon validation failure.
3. **Strict Data Type & Domain Validation.** Negative inventory counts, negative monetary sales/expenses, invalid dates, and out-of-bounds percentages must be caught at the MCP boundary and returned as structured errors.
4. **Structured Exception Propagation.** MCPs must catch all exceptions (network timeouts, rate limits, parsing errors) and wrap them in the Standard Error Response envelope. Raw stack traces must never leak to downstream agents.
5. **Read-Only V1 Scope.** All MCP integrations in V1 are strictly **read-only**. No MCP may execute write, update, or delete operations against external systems.
6. **Mandatory Audit Logging.** Every MCP execution attempt — whether returning `"success"` or `"error"` — must be written to the `audit_logs` table by the Orchestrator immediately upon MCP return.

---

## 1. Google Sheets MCP

### Purpose

Fetch inventory levels, sales transactions, expense records, and supplier master data from connected Google Sheets. This serves as the foundational operational dataset for the Inventory Agent, Finance Agent, and Supplier Agent.

---

### Input Schema

```json
{
  "spreadsheet_id": "string",
  "sheets": ["inventory", "sales", "expenses", "suppliers"],
  "date_range": {
    "start_date": "string (ISO 8601 date)",
    "end_date": "string (ISO 8601 date)"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `spreadsheet_id` | string | Yes | Google Sheets document ID loaded from environment variables |
| `sheets` | array of strings | Yes | List of sheet tabs to fetch; must contain at least one valid name |
| `date_range.start_date` | string | Yes | Start of data window; format `YYYY-MM-DD` |
| `date_range.end_date` | string | Yes | End of data window; format `YYYY-MM-DD`; must be >= `start_date` |

**Validation Rules:**
- `spreadsheet_id` must be non-empty.
- `sheets` array must be non-empty; permitted values: `"inventory"`, `"sales"`, `"expenses"`, `"suppliers"`.
- `start_date` and `end_date` must be valid calendar dates formatted as `YYYY-MM-DD`.
- `end_date` must not precede `start_date`.

---

### Output Schema

On success, `data` contains requested sheet payloads:

```json
{
  "inventory": [
    {
      "inventory_id": "string",
      "product_id": "string",
      "current_stock": "integer",
      "warehouse_location": "string | null",
      "last_updated": "string (ISO 8601 timestamp)",
      "recorded_by": "google_sheets_mcp"
    }
  ],
  "sales": [
    {
      "sale_id": "string",
      "product_id": "string",
      "quantity_sold": "integer",
      "sale_amount": "float",
      "unit_price_at_sale": "float",
      "sale_date": "string (ISO 8601 date)",
      "channel": "string | null",
      "recorded_at": "string (ISO 8601 timestamp)"
    }
  ],
  "expenses": [
    {
      "expense_id": "string",
      "expense_category": "string",
      "amount": "float",
      "description": "string | null",
      "expense_date": "string (ISO 8601 date)",
      "vendor": "string | null",
      "recorded_at": "string (ISO 8601 timestamp)"
    }
  ],
  "suppliers": [
    {
      "supplier_id": "string",
      "supplier_name": "string",
      "contact_name": "string | null",
      "contact_email": "string | null",
      "country": "string",
      "product_categories": ["string"],
      "dependency_percentage": "float | null",
      "contract_start_date": "string (ISO 8601 date) | null",
      "contract_end_date": "string (ISO 8601 date) | null",
      "is_active": "boolean",
      "created_at": "string (ISO 8601 timestamp)"
    }
  ]
}
```

**Domain Integrity Guarantees:**
- Unrequested sheets are omitted from `data`. Arrays return empty `[]` if no records match the window.
- `inventory.current_stock` is guaranteed `>= 0`. Negative values halt processing with `NEGATIVE_STOCK_VALUE`.
- `sales.quantity_sold` is guaranteed `> 0`. Zero or negative quantities halt processing with `INVALID_QUANTITY_VALUE`.
- `sales.sale_amount`, `sales.unit_price_at_sale`, and `expenses.amount` are guaranteed `>= 0.0`. Negative monetary values halt processing with `NEGATIVE_MONETARY_VALUE`.
- `suppliers.dependency_percentage` must be between `0.0` and `100.0` (or null). Out-of-range values trigger `INVALID_PERCENTAGE_VALUE`.

---

### Error Schema

| Error Code | Cause |
|---|---|
| `MISSING_SPREADSHEET_ID` | `spreadsheet_id` was empty or absent |
| `INVALID_SHEET_NAME` | `sheets` contains unrecognized sheet tab identifiers |
| `INVALID_DATE_FORMAT` | `start_date` or `end_date` violates `YYYY-MM-DD` format |
| `INVALID_DATE_RANGE` | `end_date` is chronologically before `start_date` |
| `SHEETS_AUTH_FAILED` | Google Sheets API OAuth / Service Account authentication failed |
| `SHEET_NOT_FOUND` | A requested sheet tab does not exist in the spreadsheet document |
| `FETCH_FAILED` | Upstream network connection drop or API timeout |
| `NEGATIVE_STOCK_VALUE` | Inventory record contains negative `current_stock` |
| `INVALID_QUANTITY_VALUE` | Sales record contains zero or negative `quantity_sold` |
| `NEGATIVE_MONETARY_VALUE` | Sales or expense record contains negative monetary amount |
| `INVALID_PERCENTAGE_VALUE` | Supplier record contains `dependency_percentage` < 0 or > 100 |
| `MISSING_REQUIRED_FIELD` | Mandatory cell (e.g., `product_id`, `sale_id`) is empty in sheet |

---

## 2. Calendar MCP

### Purpose

Retrieve upcoming compliance deadlines, regulatory milestones, and contract renewal schedules from connected corporate calendars. Consumed primarily by the Compliance Agent.

---

### Input Schema

```json
{
  "calendar_id": "string",
  "look_ahead_days": "integer",
  "event_types": ["tax", "license", "insurance", "regulatory", "contract_renewal", "other"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `calendar_id` | string | Yes | Corporate calendar identifier loaded via environment configuration |
| `look_ahead_days` | integer | Yes | Number of future days to scan; must be > 0 and <= 365 |
| `event_types` | array of strings | No | Filter by specific event types matching `ComplianceEvent` domain model; defaults to all |

**Validation Rules:**
- `calendar_id` must be non-empty.
- `look_ahead_days` must be an integer between 1 and 365.
- Permitted `event_types`: `"tax"`, `"license"`, `"insurance"`, `"regulatory"`, `"contract_renewal"`, `"other"`.

---

### Output Schema

On success, `data` contains:

```json
{
  "calendar_events": [
    {
      "event_id": "string",
      "event_name": "string",
      "event_type": "tax | license | insurance | regulatory | contract_renewal | other",
      "due_date": "string (ISO 8601 date)",
      "description": "string | null",
      "responsible_party": "string | null",
      "status": "pending | completed | overdue",
      "recurrence": "monthly | quarterly | annual | one_time | null"
    }
  ],
  "look_ahead_days": "integer",
  "total_events_returned": "integer"
}
```

| Field | Type | Description |
|---|---|---|
| `calendar_events` | array of objects | List of compliance events within the look-ahead window |
| `calendar_events[].event_id` | string | Unique calendar event UUID or upstream identifier |
| `calendar_events[].event_name` | string | Human-readable title of the obligation |
| `calendar_events[].event_type` | string | Categorization aligned with `ComplianceEvent.event_type` model |
| `calendar_events[].due_date` | string | Obligation deadline formatted as `YYYY-MM-DD` |
| `calendar_events[].description` | string or null | Detailed notes or filing instructions |
| `calendar_events[].responsible_party` | string or null | Assigned department, role, or individual email |
| `calendar_events[].status` | string | Execution status: `"pending"`, `"completed"`, or `"overdue"` |
| `calendar_events[].recurrence` | string or null | Frequency: `"monthly"`, `"quarterly"`, `"annual"`, `"one_time"`, or null |
| `look_ahead_days` | integer | Echo of the validated look-ahead period |
| `total_events_returned` | integer | Total count of objects in `calendar_events` |

---

### Error Schema

| Error Code | Cause |
|---|---|
| `MISSING_CALENDAR_ID` | `calendar_id` was empty or absent |
| `INVALID_LOOK_AHEAD_DAYS` | `look_ahead_days` is <= 0 or > 365 |
| `INVALID_EVENT_TYPE` | `event_types` array contains unauthorized categories |
| `CALENDAR_AUTH_FAILED` | Calendar API OAuth / token authorization rejected |
| `CALENDAR_NOT_FOUND` | Specified calendar ID does not exist or is inaccessible |
| `FETCH_FAILED` | Network failure or API rate limit during event pull |
| `INVALID_DATE_FORMAT` | Calendar entry contains malformed date string |

---

## 3. News MCP

### Purpose

Fetch recent industry developments and supplier-specific market news. Serves as optional qualitative enrichment input for the Supplier Agent.

---

### Input Schema

```json
{
  "supplier_names": ["string"],
  "industry_keywords": ["string"],
  "max_articles_per_topic": "integer",
  "max_age_days": "integer"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `supplier_names` | array of strings | Conditional | Target supplier entities to monitor |
| `industry_keywords` | array of strings | Conditional | Target macro-industry topics to monitor |
| `max_articles_per_topic` | integer | No | Cap on results per query item; defaults to 5 (max 25) |
| `max_age_days` | integer | No | Look-back window in days; defaults to 30 (max 90) |

**Validation Rules:**
- At least one of `supplier_names` or `industry_keywords` must be non-empty.
- `max_articles_per_topic` must be between 1 and 25.
- `max_age_days` must be between 1 and 90.

---

### Output Schema

On success, `data` contains:

```json
{
  "supplier_news": [
    {
      "article_id": "string",
      "supplier_name": "string",
      "headline": "string",
      "summary": "string",
      "source": "string",
      "published_date": "string (ISO 8601 date)",
      "sentiment": "positive | neutral | negative",
      "url": "string | null"
    }
  ],
  "industry_news": [
    {
      "article_id": "string",
      "keyword": "string",
      "headline": "string",
      "summary": "string",
      "source": "string",
      "published_date": "string (ISO 8601 date)",
      "sentiment": "positive | neutral | negative",
      "url": "string | null"
    }
  ],
  "total_supplier_articles": "integer",
  "total_industry_articles": "integer"
}
```

| Field | Type | Description |
|---|---|---|
| `supplier_news` | array of objects | News items matched directly to specified supplier names |
| `supplier_news[].article_id` | string | Unique cryptographic hash or provider ID for the article |
| `supplier_news[].supplier_name` | string | Exact input supplier string that triggered this match |
| `supplier_news[].headline` | string | Published article title |
| `supplier_news[].summary` | string | Copyright-safe abstract or summary (maximum 500 characters) |
| `supplier_news[].source` | string | Publishing outlet name (e.g., `"Reuters"`, `"Bloomberg"`) |
| `supplier_news[].published_date` | string | Publication date formatted as `YYYY-MM-DD` |
| `supplier_news[].sentiment` | string | NLP sentiment indicator: `"positive"`, `"neutral"`, or `"negative"` |
| `supplier_news[].url` | string or null | Canonical web URL to original publication |
| `industry_news` | array of objects | News items matched to macro industry search terms |
| `industry_news[].article_id` | string | Unique cryptographic hash or provider ID for the article |
| `industry_news[].keyword` | string | Exact industry keyword term that triggered this match |
| `industry_news[].headline` | string | Published article title |
| `industry_news[].summary` | string | Copyright-safe abstract or summary (maximum 500 characters) |
| `industry_news[].source` | string | Publishing outlet name |
| `industry_news[].published_date` | string | Publication date formatted as `YYYY-MM-DD` |
| `industry_news[].sentiment` | string | NLP sentiment indicator: `"positive"`, `"neutral"`, or `"negative"` |
| `industry_news[].url` | string or null | Canonical web URL to original publication |
| `total_supplier_articles` | integer | Total count of items in `supplier_news` |
| `total_industry_articles` | integer | Total count of items in `industry_news` |

---

### Error Schema

| Error Code | Cause |
|---|---|
| `MISSING_SEARCH_TERMS` | Both `supplier_names` and `industry_keywords` were empty or null |
| `INVALID_MAX_ARTICLES` | `max_articles_per_topic` is <= 0 or > 25 |
| `INVALID_MAX_AGE` | `max_age_days` is <= 0 or > 90 |
| `NEWS_API_AUTH_FAILED` | Upstream news aggregator API authentication rejected |
| `FETCH_FAILED` | Aggregator connection timeout or HTTP error |
| `RATE_LIMIT_EXCEEDED` | Upstream API quota exhausted |

---

## 4. Supplier Intelligence MCP

### Purpose

Retrieve enriched vendor profiles, historical delivery performance metrics, and pre-computed risk flags. Acts as the primary structured intelligence feed for the Supplier Agent.

---

### Input Schema

```json
{
  "supplier_ids": ["string"],
  "include_history": "boolean",
  "history_months": "integer"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `supplier_ids` | array of strings | Yes | List of unique supplier UUIDs to enrich |
| `include_history` | boolean | No | Whether to pull historical fulfillment series; defaults to `true` |
| `history_months` | integer | No | Depth of monthly history (1–24); defaults to 6 |

**Validation Rules:**
- `supplier_ids` must contain at least 1 non-empty string identifier.
- `history_months` must be between 1 and 24.

---

### Output Schema

On success, `data` contains:

```json
{
  "supplier_profiles": [
    {
      "supplier_id": "string",
      "supplier_name": "string",
      "country": "string",
      "product_categories": ["string"],
      "reliability_score": "integer",
      "quality_score": "integer",
      "delivery_performance": {
        "on_time_rate_percent": "float",
        "average_delay_days": "float"
      },
      "financial_stability_indicator": "stable | watch | at_risk",
      "active_since": "string (ISO 8601 date)",
      "contract_end_date": "string (ISO 8601 date) | null",
      "risk_flags": ["string"]
    }
  ],
  "supplier_history": [
    {
      "supplier_id": "string",
      "month": "string (YYYY-MM)",
      "orders_placed": "integer",
      "orders_fulfilled": "integer",
      "fulfilment_rate_percent": "float",
      "incidents": ["string"]
    }
  ],
  "supplier_risk_data": [
    {
      "supplier_id": "string",
      "risk_score": "integer",
      "risk_level": "high | medium | low",
      "primary_risk_factor": "string",
      "last_assessed": "string (ISO 8601 date)"
    }
  ],
  "total_suppliers_returned": "integer"
}
```

| Field | Type | Description |
|---|---|---|
| `supplier_profiles` | array of objects | Enriched master profiles for discovered suppliers |
| `supplier_profiles[].supplier_id` | string | Requested unique supplier UUID |
| `supplier_profiles[].supplier_name` | string | Registered legal entity name of vendor |
| `supplier_profiles[].country` | string | Primary jurisdiction of operations (ISO 3166-1 alpha-2 or full name) |
| `supplier_profiles[].product_categories` | array of strings | Commodity or service categories supplied |
| `supplier_profiles[].reliability_score` | integer | Normalized index 0–100 measuring historical fulfillment consistency |
| `supplier_profiles[].quality_score` | integer | Normalized index 0–100 measuring defect/return rates |
| `supplier_profiles[].delivery_performance.on_time_rate_percent` | float | Percentage of shipments arriving on or before promise date |
| `supplier_profiles[].delivery_performance.average_delay_days` | float | Mean delivery latency variance in days (0.0 if early/on time) |
| `supplier_profiles[].financial_stability_indicator` | string | Credit risk classification: `"stable"`, `"watch"`, or `"at_risk"` |
| `supplier_profiles[].active_since` | string | Vendor onboarding date formatted as `YYYY-MM-DD` |
| `supplier_profiles[].contract_end_date` | string or null | Current master agreement expiration date (`YYYY-MM-DD`) or null |
| `supplier_profiles[].risk_flags` | array of strings | Discrete risk tags (e.g., `"single_source"`, `"geopolitical_exposure"`) |
| `supplier_history` | array of objects | Monthly fulfillment time series; empty if `include_history` is false |
| `supplier_history[].supplier_id` | string | Vendor UUID matching profile |
| `supplier_history[].month` | string | Calendar month string formatted as `YYYY-MM` |
| `supplier_history[].orders_placed` | integer | Total purchase orders issued during month |
| `supplier_history[].orders_fulfilled` | integer | Total orders completed satisfactorily during month |
| `supplier_history[].fulfilment_rate_percent` | float | `(orders_fulfilled / orders_placed) * 100.0` |
| `supplier_history[].incidents` | array of strings | Descriptions of formal vendor infractions or quality breaches |
| `supplier_risk_data` | array of objects | Pre-computed advisory risk assessments |
| `supplier_risk_data[].supplier_id` | string | Vendor UUID matching profile |
| `supplier_risk_data[].risk_score` | integer | Aggregate vendor risk index 0–100 (100 = extreme risk) |
| `supplier_risk_data[].risk_level` | string | Categorical bracket: `"high"`, `"medium"`, or `"low"` |
| `supplier_risk_data[].primary_risk_factor` | string | Dominant risk driver (e.g., `"financial_distress"`, `"logistics_bottleneck"`) |
| `supplier_risk_data[].last_assessed` | string | Date of last upstream rating evaluation (`YYYY-MM-DD`) |
| `total_suppliers_returned` | integer | Count of profiles successfully resolved |

**Partial Resolution Handling:**
- If a requested `supplier_id` is missing in the database but at least one ID resolves, the MCP returns `status: "success"`, omits the missing ID from `data`, and appends an advisory notification to `warnings` (e.g., `"Supplier ID 'VEND-999' not found in intelligence database"`).
- If *none* of the requested IDs resolve, execution halts with error code `NO_SUPPLIERS_FOUND`.

---

### Error Schema

| Error Code | Cause |
|---|---|
| `MISSING_SUPPLIER_IDS` | `supplier_ids` array was empty or absent |
| `INVALID_HISTORY_MONTHS` | `history_months` is <= 0 or > 24 |
| `INTELLIGENCE_API_AUTH_FAILED` | External enrichment database API token rejected |
| `NO_SUPPLIERS_FOUND` | Zero requested supplier IDs resolved in the database |
| `UPSTREAM_API_TIMEOUT` | External enrichment database timed out mid-fetch |
| `CORRUPTED_PAYLOAD_ERROR` | Upstream provider returned malformed JSON structure |

---

## 5. Risk Registry MCP

### Purpose

Query historical risk scores, aggregate business status records, and multi-period trend directions from the central registry. Consumed primarily by the Risk Tracker Agent.

---

### Input Schema

```json
{
  "business_id": "string",
  "score_types": [
    "inventory_risk",
    "finance_risk",
    "supplier_risk",
    "compliance_risk",
    "business_risk",
    "business_health",
    "confidence"
  ],
  "history_days": "integer"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `business_id` | string | Yes | Unique corporate entity UUID whose risk history is queried |
| `score_types` | array of strings | No | Specific score categories to retrieve; defaults to all 7 types |
| `history_days` | integer | No | Chronological look-back window (1–365); defaults to 90 |

**Validation Rules:**
- `business_id` must be non-empty.
- Permitted `score_types`: `"inventory_risk"`, `"finance_risk"`, `"supplier_risk"`, `"compliance_risk"`, `"business_risk"`, `"business_health"`, `"confidence"`.
- `history_days` must be between 1 and 365.

---

### Output Schema

On success, `data` contains:

```json
{
  "risk_history": [
    {
      "score_id": "string",
      "agent_name": "string",
      "score_type": "string",
      "score_value": "integer",
      "run_id": "string",
      "recorded_at": "string (ISO 8601 timestamp)"
    }
  ],
  "risk_status": {
    "current_business_risk_score": "integer | null",
    "last_run_id": "string | null",
    "last_run_timestamp": "string (ISO 8601 timestamp) | null"
  },
  "risk_scores": [
    {
      "score_type": "string",
      "latest_value": "integer | null",
      "average_value": "float | null",
      "min_value": "integer | null",
      "max_value": "integer | null",
      "data_points": "integer"
    }
  ],
  "risk_trends": [
    {
      "score_type": "string",
      "trend_direction": "improving | stable | deteriorating",
      "trend_confidence": "float",
      "period_days": "integer"
    }
  ],
  "history_days": "integer",
  "total_records_returned": "integer"
}
```

| Field | Type | Description |
|---|---|---|
| `risk_history` | array of objects | Time series of discrete risk score evaluations |
| `risk_history[].score_id` | string | Unique score record UUID matching `RiskScore.score_id` model |
| `risk_history[].agent_name` | string | Identifier of the analyzing agent that produced the score |
| `risk_history[].score_type` | string | Categorical metric type (e.g., `"inventory_risk"`, `"finance_risk"`) |
| `risk_history[].score_value` | integer | Evaluated index 0–100 |
| `risk_history[].run_id` | string | Orchestrator execution pipeline run UUID |
| `risk_history[].recorded_at` | string | ISO 8601 UTC timestamp when score was persisted |
| `risk_status` | object | Latest top-level aggregate risk posture snapshot |
| `risk_status.current_business_risk_score` | integer or null | Latest composite `business_risk` evaluation (null if first run) |
| `risk_status.last_run_id` | string or null | Run UUID of most recent completed pipeline analysis |
| `risk_status.last_run_timestamp` | string or null | ISO 8601 UTC timestamp of most recent completed analysis |
| `risk_scores` | array of objects | Statistical aggregations per score type over the look-back window |
| `risk_scores[].score_type` | string | Categorical metric type |
| `risk_scores[].latest_value` | integer or null | Most recent evaluation in window |
| `risk_scores[].average_value` | float or null | Arithmetic mean of evaluations across window |
| `risk_scores[].min_value` | integer or null | Minimum evaluation across window |
| `risk_scores[].max_value` | integer or null | Maximum evaluation across window |
| `risk_scores[].data_points` | integer | Total discrete evaluation instances aggregated |
| `risk_trends` | array of objects | Multi-period regression direction indicators |
| `risk_trends[].score_type` | string | Categorical metric type |
| `risk_trends[].trend_direction` | string | Trajectory: `"improving"`, `"stable"`, or `"deteriorating"` |
| `risk_trends[].trend_confidence` | float | Statistical R² / model confidence index 0.0–1.0 |
| `risk_trends[].period_days` | integer | Look-back duration evaluated for trend calculation |
| `history_days` | integer | Echo of resolved chronological scan window |
| `total_records_returned` | integer | Total discrete records present in `risk_history` array |

---

### Error Schema

| Error Code | Cause |
|---|---|
| `MISSING_BUSINESS_ID` | `business_id` was empty or absent |
| `INVALID_SCORE_TYPE` | `score_types` array contains unauthorized categories |
| `INVALID_HISTORY_DAYS` | `history_days` is <= 0 or > 365 |
| `REGISTRY_AUTH_FAILED` | Risk Registry database API credentials rejected |
| `BUSINESS_NOT_FOUND` | No business entity registered under specified UUID |
| `DATABASE_QUERY_ERROR` | SQL / query execution failure on registry backend |

---

## Cross-MCP Data Flow Reference

The table below maps MCP outputs to their consuming analytical agents to define strict orchestrator dependency barriers.

| MCP Integration | Primary Consumer Agent | Secondary Consumer Agent(s) | Operational Dependency |
|---|---|---|---|
| **Google Sheets MCP** | Inventory Agent<br>Finance Agent | Supplier Agent | **Critical:** Core transactional & master data |
| **Calendar MCP** | Compliance Agent | — | **Critical:** Regulatory & renewal schedules |
| **News MCP** | Supplier Agent | — | **Advisory:** Qualitative sentiment signals |
| **Supplier Intelligence MCP** | Supplier Agent | — | **Critical:** External vendor benchmarks |
| **Risk Registry MCP** | Risk Tracker Agent | — | **Advisory:** Historical baseline series |

**Orchestration Mandate:** All five MCPs execute during the MCP Initialization Phase. The Orchestrator must not dispatch downstream analytical agents until all mandatory MCPs return successful response envelopes.

---

## MCP Error Handling & Resilience Policy

When an MCP returns a `Standard Error Response`, the Orchestrator executes the following deterministic resilience sequence:

1. **Mandatory Audit Event:** Write the complete error envelope (including `error_code` and `error_message`) to `audit_logs`.
2. **Pipeline Triage:** Apply the per-MCP routing rule defined below:

| MCP Integration | Failure Action | Pipeline Impact & Fallback Behavior |
|---|---|---|
| **Google Sheets MCP** | **Halt Pipeline** | Abort analysis immediately. Broadcast structured error to dashboard. Pipeline cannot execute without primary operational ledgers. |
| **Calendar MCP** | **Halt Pipeline** | Abort analysis immediately. Compliance Agent requires deterministic deadline ledgers to evaluate regulatory exposure. |
| **News MCP** | **Continue (Degraded)** | Proceed with pipeline execution. Suppress news signals; Supplier Agent executes using Sheets and Intelligence data alone. |
| **Supplier Intelligence MCP** | **Halt Pipeline** | Abort analysis immediately. Supplier Agent requires external reliability and quality benchmarks to compute valid risk scores. |
| **Risk Registry MCP** | **Continue (Degraded)** | Proceed with pipeline execution. Risk Tracker Agent defaults historical delta comparisons to `"stable"` trajectory. |

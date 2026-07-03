# DATA_MODELS.md

> **Business Guardian AI — Data Models v1.0**
> All schemas in this document are binding. Do not modify fields, types, or validation rules without team approval and constitution amendment.

---

## Schema Conventions

- All `id` fields are strings (UUIDs or slugs).
- All timestamps are ISO 8601 strings: `"YYYY-MM-DDTHH:MM:SSZ"`.
- All dates are ISO 8601 date strings: `"YYYY-MM-DD"`.
- All monetary values are floats rounded to 2 decimal places.
- All score fields are integers in the range 0–100.
- `required` lists the fields that must be present and non-null.
- `nullable` fields may be null/None but must be present in the object.

---

## 1. Product

**Purpose:** Represents a single product in the business catalog.

```json
{
  "$schema": "Product",
  "type": "object",
  "fields": {
    "product_id": {
      "type": "string",
      "description": "Unique product identifier (UUID or SKU)",
      "required": true
    },
    "product_name": {
      "type": "string",
      "description": "Human-readable product name",
      "required": true
    },
    "category": {
      "type": "string",
      "description": "Product category label",
      "required": true
    },
    "sku": {
      "type": "string",
      "description": "Stock Keeping Unit code",
      "required": false,
      "nullable": true
    },
    "unit_cost": {
      "type": "float",
      "description": "Cost per unit in local currency",
      "required": true,
      "validation": "must be >= 0"
    },
    "unit_price": {
      "type": "float",
      "description": "Selling price per unit in local currency",
      "required": true,
      "validation": "must be >= 0"
    },
    "reorder_point": {
      "type": "integer",
      "description": "Stock level that triggers a reorder recommendation",
      "required": true,
      "validation": "must be >= 0"
    },
    "reorder_quantity": {
      "type": "integer",
      "description": "Default quantity to reorder when reorder point is reached",
      "required": true,
      "validation": "must be > 0"
    },
    "supplier_id": {
      "type": "string",
      "description": "Foreign key reference to supplier",
      "required": false,
      "nullable": true
    },
    "is_active": {
      "type": "boolean",
      "description": "Whether the product is currently active in the catalog",
      "required": true
    },
    "created_at": {
      "type": "string (ISO 8601)",
      "description": "Record creation timestamp",
      "required": true
    }
  }
}
```

---

## 2. InventoryRecord

**Purpose:** Represents the current stock level for a single product.

```json
{
  "$schema": "InventoryRecord",
  "type": "object",
  "fields": {
    "inventory_id": {
      "type": "string",
      "description": "Unique inventory record identifier",
      "required": true
    },
    "product_id": {
      "type": "string",
      "description": "Foreign key reference to product",
      "required": true
    },
    "current_stock": {
      "type": "integer",
      "description": "Current quantity in stock",
      "required": true,
      "validation": "must be >= 0; negative values are rejected"
    },
    "warehouse_location": {
      "type": "string",
      "description": "Physical or logical location of the stock",
      "required": false,
      "nullable": true
    },
    "last_updated": {
      "type": "string (ISO 8601)",
      "description": "Timestamp of the most recent stock update",
      "required": true
    },
    "recorded_by": {
      "type": "string",
      "description": "Source of the update (e.g., 'google_sheets_mcp', 'manual')",
      "required": true
    }
  }
}
```

---

## 3. SalesRecord

**Purpose:** Represents a single sales transaction.

```json
{
  "$schema": "SalesRecord",
  "type": "object",
  "fields": {
    "sale_id": {
      "type": "string",
      "description": "Unique sale identifier",
      "required": true
    },
    "product_id": {
      "type": "string",
      "description": "Foreign key reference to product",
      "required": true
    },
    "quantity_sold": {
      "type": "integer",
      "description": "Number of units sold in this transaction",
      "required": true,
      "validation": "must be > 0"
    },
    "sale_amount": {
      "type": "float",
      "description": "Total revenue from this sale",
      "required": true,
      "validation": "must be > 0"
    },
    "unit_price_at_sale": {
      "type": "float",
      "description": "Price per unit at time of sale",
      "required": true,
      "validation": "must be >= 0"
    },
    "sale_date": {
      "type": "string (ISO 8601 date)",
      "description": "Date the sale occurred",
      "required": true,
      "validation": "must be a valid date; future dates rejected"
    },
    "channel": {
      "type": "string",
      "description": "Sales channel (e.g., 'in_store', 'online', 'wholesale')",
      "required": false,
      "nullable": true
    },
    "recorded_at": {
      "type": "string (ISO 8601)",
      "description": "Timestamp when the record was created",
      "required": true
    }
  }
}
```

---

## 4. ExpenseRecord

**Purpose:** Represents a single business expense entry.

```json
{
  "$schema": "ExpenseRecord",
  "type": "object",
  "fields": {
    "expense_id": {
      "type": "string",
      "description": "Unique expense identifier",
      "required": true
    },
    "expense_category": {
      "type": "string",
      "description": "Category of the expense (e.g., 'rent', 'salaries', 'utilities', 'inventory')",
      "required": true
    },
    "amount": {
      "type": "float",
      "description": "Expense amount in local currency",
      "required": true,
      "validation": "must be > 0"
    },
    "description": {
      "type": "string",
      "description": "Human-readable description of the expense",
      "required": false,
      "nullable": true
    },
    "expense_date": {
      "type": "string (ISO 8601 date)",
      "description": "Date the expense was incurred",
      "required": true,
      "validation": "must be a valid date"
    },
    "vendor": {
      "type": "string",
      "description": "Name of the vendor or payee",
      "required": false,
      "nullable": true
    },
    "recorded_at": {
      "type": "string (ISO 8601)",
      "description": "Timestamp when the record was created",
      "required": true
    }
  }
}
```

---

## 5. SupplierRecord

**Purpose:** Represents a business supplier.

```json
{
  "$schema": "SupplierRecord",
  "type": "object",
  "fields": {
    "supplier_id": {
      "type": "string",
      "description": "Unique supplier identifier",
      "required": true
    },
    "supplier_name": {
      "type": "string",
      "description": "Legal or trading name of the supplier",
      "required": true
    },
    "contact_name": {
      "type": "string",
      "description": "Primary contact person at the supplier",
      "required": false,
      "nullable": true
    },
    "contact_email": {
      "type": "string",
      "description": "Primary contact email address",
      "required": false,
      "nullable": true
    },
    "country": {
      "type": "string",
      "description": "Country where the supplier is based",
      "required": true
    },
    "product_categories": {
      "type": "array of strings",
      "description": "Categories of products supplied",
      "required": true
    },
    "dependency_percentage": {
      "type": "float",
      "description": "Percentage of total purchases from this supplier",
      "required": false,
      "nullable": true,
      "validation": "0.0 to 100.0"
    },
    "contract_start_date": {
      "type": "string (ISO 8601 date)",
      "description": "Start date of current supplier contract",
      "required": false,
      "nullable": true
    },
    "contract_end_date": {
      "type": "string (ISO 8601 date)",
      "description": "End date of current supplier contract",
      "required": false,
      "nullable": true
    },
    "is_active": {
      "type": "boolean",
      "description": "Whether this supplier is currently active",
      "required": true
    },
    "created_at": {
      "type": "string (ISO 8601)",
      "description": "Record creation timestamp",
      "required": true
    }
  }
}
```

---

## 6. ComplianceEvent

**Purpose:** Represents a compliance deadline, regulatory obligation, or renewal date.

```json
{
  "$schema": "ComplianceEvent",
  "type": "object",
  "fields": {
    "event_id": {
      "type": "string",
      "description": "Unique compliance event identifier",
      "required": true
    },
    "event_name": {
      "type": "string",
      "description": "Name of the compliance obligation (e.g., 'GST Filing Q1')",
      "required": true
    },
    "event_type": {
      "type": "string",
      "description": "Type of compliance obligation: 'tax', 'license', 'insurance', 'regulatory', 'contract_renewal', 'other'",
      "required": true,
      "validation": "must be one of the permitted values"
    },
    "due_date": {
      "type": "string (ISO 8601 date)",
      "description": "Date by which the obligation must be fulfilled",
      "required": true,
      "validation": "must be a valid date"
    },
    "description": {
      "type": "string",
      "description": "Detailed description of the compliance obligation",
      "required": false,
      "nullable": true
    },
    "responsible_party": {
      "type": "string",
      "description": "Person or role responsible for this obligation",
      "required": false,
      "nullable": true
    },
    "status": {
      "type": "string",
      "description": "Current status: 'pending', 'completed', 'overdue'",
      "required": true,
      "validation": "must be one of the permitted values"
    },
    "recurrence": {
      "type": "string",
      "description": "Recurrence pattern if applicable: 'monthly', 'quarterly', 'annual', 'one_time'",
      "required": false,
      "nullable": true
    },
    "created_at": {
      "type": "string (ISO 8601)",
      "description": "Record creation timestamp",
      "required": true
    }
  }
}
```

---

## 7. RiskScore

**Purpose:** Stores a historical risk score record from any agent.

```json
{
  "$schema": "RiskScore",
  "type": "object",
  "fields": {
    "score_id": {
      "type": "string",
      "description": "Unique risk score record identifier",
      "required": true
    },
    "agent_name": {
      "type": "string",
      "description": "Name of the agent that produced this score",
      "required": true
    },
    "score_type": {
      "type": "string",
      "description": "Type of score: 'inventory_risk', 'finance_risk', 'supplier_risk', 'compliance_risk', 'business_risk', 'business_health', 'confidence'",
      "required": true
    },
    "score_value": {
      "type": "integer",
      "description": "The numeric score value",
      "required": true,
      "validation": "0 to 100"
    },
    "run_id": {
      "type": "string",
      "description": "Identifier linking this score to a specific analysis run",
      "required": true
    },
    "recorded_at": {
      "type": "string (ISO 8601)",
      "description": "Timestamp when this score was recorded",
      "required": true
    }
  }
}
```

---

## 8. InventoryRiskReport

**Purpose:** Complete output schema of the Inventory Agent.

```json
{
  "$schema": "InventoryRiskReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "inventory_agent", "required": true },
    "inventory_risk_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "stockout_prediction": {
      "type": "array",
      "required": true,
      "items": {
        "product_id": { "type": "string", "required": true },
        "product_name": { "type": "string", "required": true },
        "current_stock": { "type": "integer", "required": true },
        "days_until_stockout": { "type": "integer", "required": true }
      }
    },
    "reorder_recommendation": {
      "type": "array",
      "required": true,
      "items": {
        "product_id": { "type": "string", "required": true },
        "product_name": { "type": "string", "required": true },
        "recommended_reorder_qty": { "type": "integer", "required": true },
        "reason": { "type": "string", "required": true }
      }
    },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 9. FinanceReport

**Purpose:** Complete output schema of the Finance Agent.

```json
{
  "$schema": "FinanceReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "finance_agent", "required": true },
    "finance_risk_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "profit_margin": { "type": "float", "required": true, "description": "Percentage, may be negative" },
    "total_revenue": { "type": "float", "required": true, "validation": ">= 0" },
    "total_expenses": { "type": "float", "required": true, "validation": ">= 0" },
    "net_profit": { "type": "float", "required": true, "description": "May be negative" },
    "financial_recommendation": { "type": "string", "required": true },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 10. SupplierRiskReport

**Purpose:** Complete output schema of the Supplier Agent.

```json
{
  "$schema": "SupplierRiskReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "supplier_agent", "required": true },
    "supplier_risk_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "dependency_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "high_risk_suppliers": {
      "type": "array",
      "required": true,
      "items": {
        "supplier_id": { "type": "string", "required": true },
        "supplier_name": { "type": "string", "required": true },
        "risk_reason": { "type": "string", "required": true },
        "risk_level": { "type": "string", "required": true, "validation": "'high', 'medium', or 'low'" }
      }
    },
    "supplier_recommendation": { "type": "string", "required": true },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 11. ComplianceReport

**Purpose:** Complete output schema of the Compliance Agent.

```json
{
  "$schema": "ComplianceReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "compliance_agent", "required": true },
    "compliance_risk_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "deadline_alerts": {
      "type": "array",
      "required": true,
      "items": {
        "event_id": { "type": "string", "required": true },
        "event_name": { "type": "string", "required": true },
        "due_date": { "type": "string (ISO 8601 date)", "required": true },
        "days_remaining": { "type": "integer", "required": true },
        "status": { "type": "string", "required": true, "validation": "'overdue', 'due_soon', or 'upcoming'" },
        "severity": { "type": "string", "required": true, "validation": "'critical', 'high', 'medium', or 'low'" }
      }
    },
    "compliance_recommendation": { "type": "string", "required": true },
    "overdue_count": { "type": "integer", "required": true, "validation": ">= 0" },
    "due_soon_count": { "type": "integer", "required": true, "validation": ">= 0" },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 12. BusinessRiskReport

**Purpose:** Complete output schema of the Risk Tracker Agent.

```json
{
  "$schema": "BusinessRiskReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "risk_tracker_agent", "required": true },
    "business_risk_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "risk_breakdown": {
      "type": "object",
      "required": true,
      "fields": {
        "inventory_risk_score": { "type": "integer", "required": true },
        "finance_risk_score": { "type": "integer", "required": true },
        "supplier_risk_score": { "type": "integer", "required": true },
        "compliance_risk_score": { "type": "integer", "required": true }
      }
    },
    "risk_trend": {
      "type": "string",
      "required": true,
      "validation": "'improving', 'stable', or 'deteriorating'"
    },
    "critical_risks": {
      "type": "array",
      "required": true,
      "items": {
        "domain": { "type": "string", "required": true },
        "score": { "type": "integer", "required": true },
        "severity": { "type": "string", "required": true, "validation": "'critical', 'high', or 'medium'" }
      }
    },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 13. StrategyReport

**Purpose:** Complete output schema of the Strategy Agent.

```json
{
  "$schema": "StrategyReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "strategy_agent", "required": true },
    "business_health_score": { "type": "integer", "required": true, "validation": "0 to 100" },
    "priority_1_action": {
      "type": "object",
      "required": true,
      "fields": {
        "action_title": { "type": "string", "required": true },
        "action_description": { "type": "string", "required": true },
        "target_domain": { "type": "string", "required": true, "validation": "'inventory', 'finance', 'supplier', or 'compliance'" },
        "urgency": { "type": "string", "required": true, "validation": "'immediate', 'this_week', or 'this_month'" },
        "expected_impact": { "type": "string", "required": true }
      }
    },
    "priority_2_action": {
      "type": "object",
      "required": true,
      "fields": {
        "action_title": { "type": "string", "required": true },
        "action_description": { "type": "string", "required": true },
        "target_domain": { "type": "string", "required": true, "validation": "'inventory', 'finance', 'supplier', or 'compliance'" },
        "urgency": { "type": "string", "required": true, "validation": "'immediate', 'this_week', or 'this_month'" },
        "expected_impact": { "type": "string", "required": true }
      }
    },
    "priority_3_action": {
      "type": "object",
      "required": true,
      "fields": {
        "action_title": { "type": "string", "required": true },
        "action_description": { "type": "string", "required": true },
        "target_domain": { "type": "string", "required": true, "validation": "'inventory', 'finance', 'supplier', or 'compliance'" },
        "urgency": { "type": "string", "required": true, "validation": "'immediate', 'this_week', or 'this_month'" },
        "expected_impact": { "type": "string", "required": true }
      }
    },
    "rationale": { "type": "string", "required": true },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 14. CommunicationDraft

**Purpose:** Complete output schema of the Communication Agent.

```json
{
  "$schema": "CommunicationDraft",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "communication_agent", "required": true },
    "report_draft": {
      "type": "object",
      "nullable": true,
      "fields": {
        "title": { "type": "string", "required": true },
        "executive_summary": { "type": "string", "required": true },
        "risk_summary": { "type": "string", "required": true },
        "recommended_actions": {
          "type": "array of strings",
          "required": true,
          "validation": "exactly 3 items"
        },
        "business_health_score": { "type": "integer", "required": true },
        "generated_at": { "type": "string (ISO 8601)", "required": true }
      }
    },
    "email_draft": {
      "type": "object",
      "nullable": true,
      "fields": {
        "subject": { "type": "string", "required": true },
        "recipient_name": { "type": "string", "required": false, "nullable": true },
        "body": { "type": "string", "required": true },
        "generated_at": { "type": "string (ISO 8601)", "required": true }
      }
    },
    "approval_required": {
      "type": "boolean",
      "required": true,
      "validation": "always true"
    },
    "approval_status": {
      "type": "string",
      "required": true,
      "validation": "'pending', 'approved', or 'rejected'"
    },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 15. EvaluationReport

**Purpose:** Complete output schema of the Evaluation Agent.

```json
{
  "$schema": "EvaluationReport",
  "type": "object",
  "fields": {
    "agent": { "type": "string", "value": "evaluation_agent", "required": true },
    "confidence_score": {
      "type": "integer",
      "required": true,
      "validation": "0 to 100; if < 60, human_review_flag must be true"
    },
    "validation_status": {
      "type": "string",
      "required": true,
      "validation": "'passed', 'passed_with_warnings', or 'failed'"
    },
    "human_review_flag": {
      "type": "boolean",
      "required": true,
      "validation": "true if confidence_score < 60 or validation_status is 'failed'"
    },
    "validation_details": {
      "type": "array",
      "required": true,
      "items": {
        "agent_name": { "type": "string", "required": true },
        "validation_passed": { "type": "boolean", "required": true },
        "issues_found": { "type": "array of strings", "required": true }
      }
    },
    "warnings": {
      "type": "array",
      "required": true,
      "items": {
        "warning_code": { "type": "string", "required": true },
        "warning_message": { "type": "string", "required": true },
        "affected_agent": { "type": "string", "required": true }
      }
    },
    "status": { "type": "string", "required": true, "validation": "'success' or 'error'" },
    "timestamp": { "type": "string (ISO 8601)", "required": true }
  }
}
```

---

## 16. AuditLog

**Purpose:** Records every agent action, MCP call, and pipeline event for full audit traceability. Written by the Orchestrator — never by agents directly. Maps to the `audit_logs` database table.

```json
{
  "$schema": "AuditLog",
  "type": "object",
  "fields": {
    "log_id": {
      "type": "string",
      "description": "Unique log entry identifier (UUID)",
      "required": true
    },
    "run_id": {
      "type": "string",
      "description": "Analysis run identifier; links all entries for a single run",
      "required": true
    },
    "event_type": {
      "type": "string",
      "description": "Type of event: 'pipeline_start', 'pipeline_complete', 'pipeline_error', 'mcp_call_start', 'mcp_call_complete', 'mcp_call_error', 'agent_dispatch', 'agent_complete', 'agent_error', 'agent_retry', 'guardrail_validation_failed', 'guardrail_hitl_pending', 'guardrail_hitl_approved', 'guardrail_hitl_rejected', 'guardrail_confidence_flagged'",
      "required": true,
      "validation": "must be one of the permitted event_type values"
    },
    "agent_name": {
      "type": "string",
      "description": "Name of the agent; null for MCP and pipeline-level events",
      "required": false,
      "nullable": true
    },
    "input_payload": {
      "type": "object",
      "description": "Serialized input passed to the agent or MCP; null for pipeline-level events",
      "required": false,
      "nullable": true
    },
    "output_payload": {
      "type": "object",
      "description": "Serialized output received from the agent or MCP; null if not yet available",
      "required": false,
      "nullable": true
    },
    "status": {
      "type": "string",
      "description": "Outcome of the logged event",
      "required": true,
      "validation": "'success', 'error', 'retry', or 'skipped'"
    },
    "error_code": {
      "type": "string",
      "description": "Structured error code if status is 'error'; null otherwise",
      "required": false,
      "nullable": true
    },
    "duration_ms": {
      "type": "integer",
      "description": "Execution duration in milliseconds",
      "required": false,
      "nullable": true
    },
    "timestamp": {
      "type": "string (ISO 8601)",
      "description": "Timestamp of when this event occurred",
      "required": true
    }
  }
}
```

---

## 17. Report

**Purpose:** Stores generated analysis reports for retrieval via the FastAPI backend and display on the Streamlit dashboard. Maps to the `reports` database table.

```json
{
  "$schema": "Report",
  "type": "object",
  "fields": {
    "report_id": {
      "type": "string",
      "description": "Unique report identifier (UUID)",
      "required": true
    },
    "run_id": {
      "type": "string",
      "description": "Analysis run identifier this report was generated from",
      "required": true
    },
    "business_id": {
      "type": "string",
      "description": "Identifier of the business this report belongs to",
      "required": true
    },
    "business_name": {
      "type": "string",
      "description": "Human-readable name of the business",
      "required": true
    },
    "report_type": {
      "type": "string",
      "description": "Category of the report content",
      "required": true,
      "validation": "'full_analysis', 'risk_summary', or 'communication_draft'"
    },
    "content": {
      "type": "object",
      "description": "Full structured report content — e.g., a CommunicationDraft or assembled dashboard payload",
      "required": true
    },
    "system_status": {
      "type": "string",
      "description": "Pipeline status at the time this report was generated",
      "required": true,
      "validation": "'success', 'human_review_required', 'awaiting_human_approval', 'degraded', or 'error'"
    },
    "generated_at": {
      "type": "string (ISO 8601)",
      "description": "Timestamp when the report was generated and stored",
      "required": true
    }
  }
}
```

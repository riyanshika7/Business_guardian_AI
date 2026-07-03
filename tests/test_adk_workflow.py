"""Tests for Google ADK 2.0 Workflows and state transitions."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
import asyncio
from google.adk.sessions import InMemorySessionService
from google.adk import Runner
from google.genai.types import Content, Part
from Orchestrator import workflow

@pytest.mark.asyncio
async def test_adk_workflow_phase_1_execution(mock_db, baseline_inputs):
    """Verify that phase_1_workflow executes correctly and populates ADK session states."""
    
    # Initialize baseline workflow state
    state = {
        "run_id": "test-run-12345",
        "business_id": "BIZ-101",
        "business_name": "Bean Cafe Ltd",
        "business_type": "retail",
        "recipient_name": "Alice",
        "communication_type": "both",
        "period_days": 30,
        "analysis_window_days": 30,
        "products": baseline_inputs["products"],
        "mcp_data": {
            "google_sheets_mcp_status": "success",
            "inventory_data": baseline_inputs["inventory"],
            "sales_data": baseline_inputs["sales"],
            "expenses_data": baseline_inputs["expenses"],
            "supplier_data": baseline_inputs["suppliers"],
            "calendar_mcp_status": "success",
            "compliance_data": baseline_inputs["compliance_events"],
            "risk_registry_mcp_status": "success",
            "risk_history": []
        }
    }
    
    # Execute Phase 1 workflow
    await workflow.execute_pipeline_phase_1(state)
    
    # Assertions
    assert state["system_status"] == "awaiting_human_approval"
    assert "inventory_risk_report" in state["agent_reports"]
    assert "finance_risk_report" in state["agent_reports"]
    assert "supplier_risk_report" in state["agent_reports"]
    assert "compliance_risk_report" in state["agent_reports"]
    assert "business_risk_report" in state["agent_reports"]
    assert "strategy_report" in state["agent_reports"]
    assert "communication_draft" in state["agent_reports"]
    
    # Audit trail and metrics
    assert len(state["audit_trail"]) > 0
    assert "core_agents_layer" in state["execution_metadata"]
    assert "communication_agent" in state["execution_metadata"]

@pytest.mark.asyncio
async def test_adk_workflow_phase_2_approved(mock_db, baseline_inputs):
    """Verify that phase_2_workflow handles approval and database persistence correctly."""
    
    # Set up a state matching the end of Phase 1
    state = {
        "run_id": "test-run-12345",
        "business_id": "BIZ-101",
        "business_name": "Bean Cafe Ltd",
        "business_type": "retail",
        "recipient_name": "Alice",
        "communication_type": "both",
        "period_days": 30,
        "analysis_window_days": 30,
        "products": baseline_inputs["products"],
        "mcp_data": {
            "google_sheets_mcp_status": "success",
            "inventory_data": baseline_inputs["inventory"],
            "sales_data": baseline_inputs["sales"],
            "expenses_data": baseline_inputs["expenses"],
            "supplier_data": baseline_inputs["suppliers"],
            "calendar_mcp_status": "success",
            "compliance_data": baseline_inputs["compliance_events"],
            "risk_registry_mcp_status": "success",
            "risk_history": []
        },
        "agent_reports": {
            "inventory_risk_report": {
                "agent": "inventory_agent",
                "status": "success",
                "inventory_risk_score": 40
            },
            "finance_risk_report": {
                "agent": "finance_agent",
                "status": "success",
                "finance_risk_score": 50,
                "total_revenue": 1000.0,
                "total_expenses": 2000.0,
                "profit_margin": -100.0,
                "financial_recommendation": "Optimize",
                "timestamp": "2026-06-26T12:00:00Z"
            },
            "supplier_risk_report": {
                "agent": "supplier_agent",
                "status": "success",
                "supplier_risk_score": 30,
                "dependency_score": 40,
                "high_risk_suppliers": [],
                "supplier_recommendation": "Diversify",
                "timestamp": "2026-06-26T12:00:00Z"
            },
            "compliance_risk_report": {
                "agent": "compliance_agent",
                "status": "success",
                "compliance_risk_score": 20,
                "deadline_alerts": [],
                "overdue_count": 0,
                "due_soon_count": 1,
                "compliance_recommendation": "Address",
                "timestamp": "2026-06-26T12:00:00Z"
            },
            "business_risk_report": {
                "agent": "risk_tracker_agent",
                "status": "success",
                "business_risk_score": 37,
                "risk_breakdown": {
                    "inventory_risk_score": 40,
                    "finance_risk_score": 50,
                    "supplier_risk_score": 30,
                    "compliance_risk_score": 20
                },
                "risk_trend": "stable",
                "critical_risks": [],
                "timestamp": "2026-06-26T12:00:00Z"
            },
            "strategy_report": {
                "agent": "strategy_agent",
                "status": "success",
                "business_health_score": 63,
                "priority_1_action": {
                    "action_title": "Fix",
                    "action_description": "Fix issues",
                    "target_domain": "finance",
                    "urgency": "immediate",
                    "expected_impact": "Impact"
                },
                "priority_2_action": {
                    "action_title": "Fix 2",
                    "action_description": "Fix issues 2",
                    "target_domain": "inventory",
                    "urgency": "this_week",
                    "expected_impact": "Impact"
                },
                "priority_3_action": {
                    "action_title": "Fix 3",
                    "action_description": "Fix issues 3",
                    "target_domain": "supplier",
                    "urgency": "this_month",
                    "expected_impact": "Impact"
                },
                "rationale": "Rationale",
                "timestamp": "2026-06-26T12:00:00Z"
            },
            "communication_draft": {
                "agent": "communication_agent",
                "status": "success",
                "report_draft": {
                    "title": "Ops briefing",
                    "executive_summary": "Overall health normal",
                    "risk_summary": "Finance risk elevated",
                    "recommended_actions": [],
                    "business_health_score": 63,
                    "generated_at": "2026-06-26T12:00:00Z"
                },
                "email_draft": {
                    "subject": "Ops summary",
                    "recipient_name": "Alice",
                    "body": "Bean Cafe Ltd summary is normal",
                    "generated_at": "2026-06-26T12:00:00Z"
                },
                "approval_required": True,
                "approval_status": "pending",
                "timestamp": "2026-06-26T12:00:00Z"
            }
        }
    }
    
    from guardrails import hitl_guardrail
    hitl_pending = hitl_guardrail.create_hitl_pending_state(state["agent_reports"]["communication_draft"], state["run_id"])
    state["guardrail_state"] = {
        "approval_id": hitl_pending["approval_id"],
        "human_approval_status": "pending"
    }
    
    # Execute Phase 2 approved workflow
    await workflow.execute_pipeline_phase_2(state, approved=True)
    
    # Assertions
    assert state["system_status"] in ("success", "human_review_required")
    assert state["guardrail_state"]["human_approval_status"] == "approved"
    assert "evaluation_report" in state["agent_reports"]
    
    # Database persistence assertion via mock
    assert "reports" in mock_db
    assert mock_db["reports"]["run_id"] == "test-run-12345"
    assert mock_db["reports"]["system_status"] == state["system_status"]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

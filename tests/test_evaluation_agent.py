"""Tests for Evaluation Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import evaluation_agent

@pytest.fixture
def mock_all_reports():
    return {
        "inventory_risk_report": {
            "agent": "inventory_agent",
            "status": "success",
            "inventory_risk_score": 40,
            "stockout_prediction": [],
            "reorder_recommendation": [],
            "timestamp": "2026-06-26T12:00:00Z"
        },
        "finance_risk_report": {
            "agent": "finance_agent",
            "status": "success",
            "finance_risk_score": 50,
            "total_revenue": 1000.0,
            "total_expenses": 2000.0,
            "profit_margin": -100.0,
            "financial_recommendation": "Cut costs",
            "timestamp": "2026-06-26T12:00:00Z"
        },
        "supplier_risk_report": {
            "agent": "supplier_agent",
            "status": "success",
            "supplier_risk_score": 30,
            "dependency_score": 40,
            "high_risk_suppliers": [],
            "supplier_recommendation": "Diversify bases",
            "timestamp": "2026-06-26T12:00:00Z"
        },
        "compliance_risk_report": {
            "agent": "compliance_agent",
            "status": "success",
            "compliance_risk_score": 20,
            "deadline_alerts": [],
            "overdue_count": 0,
            "due_soon_count": 1,
            "compliance_recommendation": "Address upcoming audits",
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
                "action_title": "Fix Finance Issues",
                "action_description": "Optimize margins",
                "target_domain": "finance",
                "urgency": "immediate",
                "expected_impact": "Reduce losses"
            },
            "priority_2_action": {
                "action_title": "Restock Items",
                "action_description": "Replenish stockout critical products",
                "target_domain": "inventory",
                "urgency": "this_week",
                "expected_impact": "Ensure sales continuity"
            },
            "priority_3_action": {
                "action_title": "Mitigate Suppliers",
                "action_description": "Diversify partners",
                "target_domain": "supplier",
                "urgency": "this_month",
                "expected_impact": "Reduce supply chain dependency"
            },
            "rationale": "High expense overhead requires immediate correction.",
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

def test_evaluation_agent_happy_path(mock_all_reports):
    result = evaluation_agent.run(mock_all_reports)
    assert result["status"] == "success"
    assert result["agent"] == "evaluation_agent"
    assert result["validation_status"] == "passed"
    assert result["confidence_score"] == 100
    assert result["human_review_flag"] is False
    assert len(result["validation_details"]) == 7

def test_evaluation_agent_missing_upstream_report(mock_all_reports):
    bad_reports = {**mock_all_reports}
    bad_reports.pop("inventory_risk_report")
    
    result = evaluation_agent.run(bad_reports)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_UPSTREAM_REPORT"

def test_evaluation_agent_validation_warnings(mock_all_reports):
    # Alter the finance risk report to trigger a schema warning (e.g. negative cost or revenue)
    bad_reports = {**mock_all_reports}
    bad_reports["finance_risk_report"] = {
        "agent": "finance_agent",
        "status": "success",
        "finance_risk_score": 120,  # Invalid risk score
        "total_revenue": 1000.0,
        "total_expenses": 2000.0,
        "profit_margin": -100.0,
        "financial_recommendation": "Cut costs",
        "timestamp": "2026-06-26T12:00:00Z"
    }
    
    result = evaluation_agent.run(bad_reports)
    assert result["status"] == "success"
    # An invalid score subtracts 15 confidence points, turning status into passed_with_warnings or failed
    assert result["confidence_score"] < 100
    assert result["validation_status"] in ("passed_with_warnings", "failed")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

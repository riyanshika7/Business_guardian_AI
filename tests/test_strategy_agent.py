"""Tests for Strategy Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import strategy_agent

@pytest.fixture
def input_reports():
    return {
        "business_risk_report": {
            "business_risk_score": 60,
            "status": "success"
        },
        "inventory_risk_report": {
            "inventory_risk_score": 40,
            "stockout_prediction": [],
            "reorder_recommendation": []
        },
        "finance_risk_report": {
            "finance_risk_score": 80,
            "total_revenue": 1000.0,
            "total_expenses": 2000.0,
            "profit_margin": -100.0
        },
        "supplier_risk_report": {
            "supplier_risk_score": 50,
            "high_risk_suppliers": []
        },
        "compliance_risk_report": {
            "compliance_risk_score": 30,
            "overdue_count": 0,
            "due_soon_count": 1
        }
    }

def test_strategy_agent_happy_path(input_reports):
    inputs = {
        **input_reports,
        "business_type": "retail"
    }
    
    result = strategy_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "strategy_agent"
    assert result["business_health_score"] == 40  # health = 100 - 60
    assert "priority_1_action" in result
    assert "priority_2_action" in result
    assert "priority_3_action" in result
    assert "rationale" in result

def test_strategy_agent_missing_input(input_reports):
    inputs = {
        "business_risk_report": input_reports["business_risk_report"]
    }
    
    result = strategy_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_DOMAIN_REPORT"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

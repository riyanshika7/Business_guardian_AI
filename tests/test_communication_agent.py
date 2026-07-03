"""Tests for Communication Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import communication_agent

@pytest.fixture
def mock_strategy_report():
    return {
        "business_health_score": 40,
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
        "rationale": "High expense overhead requires immediate correction."
    }

def test_communication_agent_happy_path(mock_strategy_report):
    inputs = {
        "strategy_report": mock_strategy_report,
        "business_name": "Bean Cafe Ltd",
        "recipient_name": "Alice",
        "communication_type": "both"
    }
    
    result = communication_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "communication_agent"
    assert result["approval_required"] is True
    assert result["approval_status"] == "pending"
    assert result["report_draft"] is not None
    assert result["email_draft"] is not None
    
    # Assert fields in drafts
    assert result["report_draft"]["business_health_score"] == 40
    assert "Alice" in result["email_draft"]["recipient_name"]
    assert "Bean Cafe Ltd" in result["email_draft"]["body"]

def test_communication_agent_missing_business_name(mock_strategy_report):
    inputs = {
        "strategy_report": mock_strategy_report,
        "recipient_name": "Alice",
        "communication_type": "both"
    }
    
    result = communication_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_BUSINESS_NAME"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

"""Tests for Risk Tracker Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import risk_tracker_agent

@pytest.fixture
def valid_reports():
    return {
        "inventory_risk_report": {
            "agent": "inventory_agent",
            "status": "success",
            "inventory_risk_score": 40
        },
        "finance_risk_report": {
            "agent": "finance_agent",
            "status": "success",
            "finance_risk_score": 50
        },
        "supplier_risk_report": {
            "agent": "supplier_agent",
            "status": "success",
            "supplier_risk_score": 30
        },
        "compliance_risk_report": {
            "agent": "compliance_agent",
            "status": "success",
            "compliance_risk_score": 20
        }
    }

def test_risk_tracker_happy_path(valid_reports):
    inputs = {
        **valid_reports,
        "risk_history": [],
        "business_type": "retail"
    }
    
    result = risk_tracker_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "risk_tracker_agent"
    # Weighted score for retail: (40 * 0.3) + (50 * 0.3) + (30 * 0.2) + (20 * 0.2) = 12 + 15 + 6 + 4 = 37
    assert result["business_risk_score"] == 37
    assert result["risk_trend"] == "stable"

def test_risk_tracker_sector_dynamic_weights(valid_reports):
    # Agriculture: (40 * 0.2) + (50 * 0.3) + (30 * 0.25) + (20 * 0.25) = 8 + 15 + 7.5 + 5 = 35.5 -> 36
    inputs = {
        **valid_reports,
        "risk_history": [],
        "business_type": "agriculture"
    }
    result = risk_tracker_agent.run(inputs)
    assert result["business_risk_score"] == 36

def test_risk_tracker_missing_report(valid_reports):
    inputs = {
        "inventory_risk_report": valid_reports["inventory_risk_report"],
        "finance_risk_report": valid_reports["finance_risk_report"],
        "business_type": "retail"
    }
    
    result = risk_tracker_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_DOMAIN_REPORT"

def test_risk_tracker_out_of_bounds_score(valid_reports):
    bad_reports = {
        **valid_reports,
        "inventory_risk_report": {
            "agent": "inventory_agent",
            "status": "success",
            "inventory_risk_score": 150  # Out of bounds
        }
    }
    inputs = {
        **bad_reports,
        "business_type": "retail"
    }
    
    result = risk_tracker_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_RISK_SCORE"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

"""Tests for Compliance Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import compliance_agent

def test_compliance_agent_happy_path(baseline_inputs):
    inputs = {
        "compliance_events": baseline_inputs["compliance_events"],
        "calendar_events": [
            {
                "event_id": "EVT-002",
                "event_name": "Tax Renewal",
                "event_type": "tax",
                "due_date": "2026-06-20",  # Overdue relative to 2026-06-26
                "status": "pending"
            }
        ],
        "analysis_window_days": 30,
        "current_date": "2026-06-26"
    }
    
    result = compliance_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "compliance_agent"
    assert "compliance_risk_score" in result
    assert result["overdue_count"] >= 1
    assert isinstance(result["deadline_alerts"], list)

def test_compliance_agent_missing_events():
    inputs = {
        "calendar_events": [],
        "analysis_window_days": 30
    }
    
    result = compliance_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_COMPLIANCE_DATA"

def test_compliance_agent_dynamic_date_override(baseline_inputs):
    # Set current date to 2026-07-20 so the EVT-001 (due 2026-07-10) is overdue
    inputs = {
        "compliance_events": baseline_inputs["compliance_events"],
        "calendar_events": [],
        "analysis_window_days": 30,
        "current_date": "2026-07-20"
    }
    
    result = compliance_agent.run(inputs)
    assert result["status"] == "success"
    # Event on 2026-07-10 is now overdue compared to current_date 2026-07-20
    assert result["overdue_count"] == 1


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

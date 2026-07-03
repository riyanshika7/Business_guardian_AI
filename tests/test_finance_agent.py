"""Tests for Finance Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import finance_agent

def test_finance_agent_happy_path(baseline_inputs):
    inputs = {
        "sales": baseline_inputs["sales"],
        "expenses": baseline_inputs["expenses"],
        "period_days": 30
    }
    
    result = finance_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "finance_agent"
    assert "finance_risk_score" in result
    assert result["total_revenue"] == 60.00
    assert result["total_expenses"] == 120.00
    assert result["net_profit"] == -60.00
    assert result["profit_margin"] == -100.00  # profit_margin = (-60 / 60) * 100

def test_finance_agent_missing_sales(baseline_inputs):
    inputs = {
        "expenses": baseline_inputs["expenses"],
        "period_days": 30
    }
    
    result = finance_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_FINANCIAL_DATA"

def test_finance_agent_zero_revenue(baseline_inputs):
    inputs = {
        "sales": [],
        "expenses": baseline_inputs["expenses"],
        "period_days": 30
    }
    
    result = finance_agent.run(inputs)
    assert result["status"] == "success"
    # Zero revenue should trigger a high risk score (default 100 in forecasting_skill)
    assert result["finance_risk_score"] == 100
    assert result["total_revenue"] == 0.0
    assert result["net_profit"] == -120.0


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

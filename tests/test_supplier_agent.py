"""Tests for Supplier Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import supplier_agent

def test_supplier_agent_happy_path(baseline_inputs):
    inputs = {
        "suppliers": baseline_inputs["suppliers"],
        "supplier_intelligence": {
            "supplier_profiles": [
                {
                    "supplier_id": "SUP-001",
                    "reliability_score": 85,
                    "financial_stability_indicator": "stable",
                    "risk_flags": []
                }
            ],
            "supplier_risk_data": [
                {
                    "supplier_id": "SUP-001",
                    "risk_level": "low",
                    "risk_score": 15,
                    "primary_risk_factor": "none"
                }
            ]
        },
        "supplier_news": [
            {
                "headline": "Good supply line",
                "sentiment": "positive",
                "relevant_supplier": "Global Supplier"
            }
        ]
    }
    
    result = supplier_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "supplier_agent"
    assert "supplier_risk_score" in result
    assert "dependency_score" in result
    assert isinstance(result["high_risk_suppliers"], list)

def test_supplier_agent_missing_suppliers():
    inputs = {
        "supplier_intelligence": {},
        "supplier_news": []
    }
    
    result = supplier_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_SUPPLIER_DATA"

def test_supplier_agent_concentration_risk(baseline_inputs):
    # One supplier representing 90% dependency
    high_dep_suppliers = [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "Global Supplier",
            "country": "UK",
            "product_categories": "Beverages",
            "dependency_percentage": 90.0,
            "is_active": 1,
            "created_at": "2026-01-01T00:00:00Z"
        }
    ]
    inputs = {
        "suppliers": high_dep_suppliers,
        "supplier_intelligence": {
            "supplier_profiles": [
                {
                    "supplier_id": "SUP-001",
                    "reliability_score": 40,  # low reliability
                    "financial_stability_indicator": "at_risk",
                    "risk_flags": ["high_delay_rate"]
                }
            ],
            "supplier_risk_data": [
                {
                    "supplier_id": "SUP-001",
                    "risk_level": "high",
                    "risk_score": 75,
                    "primary_risk_factor": "Fulfillment failure"
                }
            ]
        },
        "supplier_news": []
    }
    
    result = supplier_agent.run(inputs)
    assert result["status"] == "success"
    # Low reliability + high dependency should drive high risk score
    assert result["supplier_risk_score"] > 40
    assert len(result["high_risk_suppliers"]) > 0


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

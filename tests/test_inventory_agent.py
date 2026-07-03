"""Tests for Inventory Agent."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import pytest
from agents import inventory_agent

def test_inventory_agent_happy_path(baseline_inputs):
    inputs = {
        "products": baseline_inputs["products"],
        "inventory": baseline_inputs["inventory"],
        "sales": baseline_inputs["sales"],
        "business_type": "retail"
    }
    
    result = inventory_agent.run(inputs)
    assert result["status"] == "success"
    assert result["agent"] == "inventory_agent"
    assert "inventory_risk_score" in result
    assert isinstance(result["stockout_prediction"], list)
    assert isinstance(result["reorder_recommendation"], list)
    assert len(result["timestamp"]) > 0

def test_inventory_agent_agriculture_seasonal(baseline_inputs):
    inputs = {
        "products": baseline_inputs["products"],
        "inventory": baseline_inputs["inventory"],
        "sales": baseline_inputs["sales"],
        "business_type": "agriculture"
    }
    
    result = inventory_agent.run(inputs)
    assert result["status"] == "success"

def test_inventory_agent_missing_inventory():
    inputs = {
        "products": [],
        "sales": [],
        "business_type": "retail"
    }
    
    result = inventory_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] == "MISSING_INVENTORY_DATA"

def test_inventory_agent_invalid_negative_stock(baseline_inputs):
    bad_inventory = [{
        "inventory_id": "INV-001",
        "product_id": "PROD-001",
        "current_stock": -5,
        "recorded_by": "worker",
        "last_updated": "2026-06-26T10:00:00Z"
    }]
    inputs = {
        "products": baseline_inputs["products"],
        "inventory": bad_inventory,
        "sales": baseline_inputs["sales"],
        "business_type": "retail"
    }
    
    result = inventory_agent.run(inputs)
    assert result["status"] == "error"
    assert result["error_code"] in ("INVALID_INVENTORY_VALUE", "VALIDATION_FAILED")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))

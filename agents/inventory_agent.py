from __future__ import annotations
"""Inventory Agent — analyzes stock levels, predicts stockouts, and recommends reorder actions."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from config import ANALYSIS_WINDOW_DAYS
from skills import retail_skill, agriculture_skill
from skills.forecasting_skill import compute_inventory_risk_score

logger = logging.getLogger(__name__)

def _success_response(agent_name: str, data: dict) -> dict:
    data["status"] = "success"
    data["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return data

def _error_response(agent_name: str, error_code: str, message: str) -> dict:
    return {
        "agent": agent_name,
        "status": "error",
        "error_code": error_code,
        "error_message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

def run(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run Inventory Agent analysis.
    
    Args:
        inputs: Must contain products, inventory, sales, and business_type.
    """
    agent_name = "inventory_agent"
    try:
        products = inputs.get("products", [])
        inventory = inputs.get("inventory")
        sales = inputs.get("sales", [])
        business_type = inputs.get("business_type", "retail")
        
        # 1. Validation: Input inventory is empty or missing
        if inventory is None or len(inventory) == 0:
            return _error_response(agent_name, "MISSING_INVENTORY_DATA", "Inventory data is missing or empty.")
            
        # 2. Validation: Required fields check
        for idx, item in enumerate(inventory):
            if "product_id" not in item or "current_stock" not in item or "inventory_id" not in item:
                return _error_response(agent_name, "VALIDATION_FAILED", f"Inventory record at index {idx} is missing required fields.")
            
            # 3. Validation: Stock value must be non-negative
            try:
                stock_val = int(item["current_stock"])
                if stock_val < 0:
                    return _error_response(agent_name, "INVALID_INVENTORY_VALUE", f"Negative stock value found for product {item.get('product_id')}.")
            except (ValueError, TypeError):
                return _error_response(agent_name, "VALIDATION_FAILED", f"Invalid stock value format for product {item.get('product_id')}.")
                
        for idx, prod in enumerate(products):
            if "product_id" not in prod or "product_name" not in prod or "reorder_point" not in prod:
                return _error_response(agent_name, "VALIDATION_FAILED", f"Product record at index {idx} is missing required fields.")
                
        # 4. Dispatch to corresponding skill
        if business_type == "agriculture":
            stockout_preds = agriculture_skill.build_stockout_predictions(products, inventory, sales, ANALYSIS_WINDOW_DAYS)
            reorder_recs = agriculture_skill.build_reorder_recommendations(products, inventory, stockout_preds)
        else:
            stockout_preds = retail_skill.build_stockout_predictions(products, inventory, sales, ANALYSIS_WINDOW_DAYS)
            reorder_recs = retail_skill.build_reorder_recommendations(products, inventory, stockout_preds)
            
        # 5. Compute risk score
        risk_score = compute_inventory_risk_score(stockout_preds, reorder_recs, len(products))
        
        # 6. Format success output
        result = {
            "agent": agent_name,
            "inventory_risk_score": risk_score,
            "stockout_prediction": stockout_preds,
            "reorder_recommendation": reorder_recs
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Inventory Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")

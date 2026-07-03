from __future__ import annotations
"""Risk Tracker Agent — aggregates domain risk scores into a unified Business Risk Score."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from skills.business_health_skill import compute_business_risk_score, compute_risk_trend
from config import RISK_WEIGHTS_BY_SECTOR

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
    """Run Risk Tracker Agent analysis.
    
    Args:
        inputs: Must contain inventory_risk_report, finance_risk_report, supplier_risk_report,
                compliance_risk_report, and risk_history.
    """
    agent_name = "risk_tracker_agent"
    try:
        inventory_rep = inputs.get("inventory_risk_report")
        finance_rep = inputs.get("finance_risk_report")
        supplier_rep = inputs.get("supplier_risk_report")
        compliance_rep = inputs.get("compliance_risk_report")
        risk_history = inputs.get("risk_history", [])
        
        # 1. Validation: reports missing
        reports = {
            "inventory": inventory_rep,
            "finance": finance_rep,
            "supplier": supplier_rep,
            "compliance": compliance_rep
        }
        
        for domain, rep in reports.items():
            if rep is None:
                return _error_response(agent_name, "MISSING_DOMAIN_REPORT", f"{domain.capitalize()} risk report is missing.")
            if rep.get("status") == "error":
                return _error_response(agent_name, "UPSTREAM_AGENT_FAILED", f"Upstream agent execution failed in {domain} domain.")
                
        # 2. Extract scores and validate ranges
        try:
            inv_score = int(inventory_rep.get("inventory_risk_score", 0))
            fin_score = int(finance_rep.get("finance_risk_score", 0))
            sup_score = int(supplier_rep.get("supplier_risk_score", 0))
            com_score = int(compliance_rep.get("compliance_risk_score", 0))
        except (ValueError, TypeError):
            return _error_response(agent_name, "INVALID_RISK_SCORE", "Risk scores must be valid integers.")
            
        for score_name, score_val in [("inventory", inv_score), ("finance", fin_score), ("supplier", sup_score), ("compliance", com_score)]:
            if not (0 <= score_val <= 100):
                return _error_response(agent_name, "INVALID_RISK_SCORE", f"{score_name.capitalize()} risk score ({score_val}) is out of bounds (0-100).")
                
        # 3. Calculate weighted business risk score
        business_type = inputs.get("business_type", "retail")
        weights = RISK_WEIGHTS_BY_SECTOR.get(business_type, RISK_WEIGHTS_BY_SECTOR["retail"])
        biz_risk_score = compute_business_risk_score(inv_score, fin_score, sup_score, com_score, weights)
        
        # 4. Calculate trend
        trend = compute_risk_trend(biz_risk_score, risk_history)
        
        # 5. Extract critical risks (>70)
        critical_risks = []
        domain_scores = [
            ("inventory", inv_score),
            ("finance", fin_score),
            ("supplier", sup_score),
            ("compliance", com_score)
        ]
        for domain, score in domain_scores:
            if score > 70:
                if score >= 85:
                    severity = "critical"
                elif score >= 75:
                    severity = "high"
                else:
                    severity = "medium"
                    
                critical_risks.append({
                    "domain": domain,
                    "score": score,
                    "severity": severity
                })
                
        result = {
            "agent": agent_name,
            "business_risk_score": biz_risk_score,
            "risk_breakdown": {
                "inventory_risk_score": inv_score,
                "finance_risk_score": fin_score,
                "supplier_risk_score": sup_score,
                "compliance_risk_score": com_score
            },
            "risk_trend": trend,
            "critical_risks": critical_risks
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Risk Tracker Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")

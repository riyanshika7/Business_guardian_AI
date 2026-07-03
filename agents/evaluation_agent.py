from __future__ import annotations
"""Evaluation Agent — validates all agent outputs and assigns a pipeline confidence score."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from guardrails.validation_guardrail import validate_agent_output
from guardrails.confidence_guardrail import compute_confidence_score

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
    """Run Evaluation Agent analysis.
    
    Args:
        inputs: Must contain all 7 upstream reports: inventory_risk_report, finance_risk_report,
                supplier_risk_report, compliance_risk_report, business_risk_report, strategy_report,
                and communication_draft.
    """
    agent_name = "evaluation_agent"
    try:
        inventory_rep = inputs.get("inventory_risk_report")
        finance_rep = inputs.get("finance_risk_report")
        supplier_rep = inputs.get("supplier_risk_report")
        compliance_rep = inputs.get("compliance_risk_report")
        biz_risk_rep = inputs.get("business_risk_report")
        strategy_rep = inputs.get("strategy_report")
        comm_draft = inputs.get("communication_draft")
        
        upstream_reports = {
            "inventory_agent": inventory_rep,
            "finance_agent": finance_rep,
            "supplier_agent": supplier_rep,
            "compliance_agent": compliance_rep,
            "risk_tracker_agent": biz_risk_rep,
            "strategy_agent": strategy_rep,
            "communication_agent": comm_draft
        }
        
        # 1. Validation: check for missing upstream reports
        for name, rep in upstream_reports.items():
            if rep is None:
                return _error_response(agent_name, "MISSING_UPSTREAM_REPORT", f"Upstream report '{name}' is missing.")
                
        # 2. Run validations on each agent
        validation_details = []
        any_failed = False
        
        for name, rep in upstream_reports.items():
            passed, issues = validate_agent_output(name, rep)
            validation_details.append({
                "agent_name": name,
                "validation_passed": passed,
                "issues_found": issues
            })
            if not passed:
                any_failed = True
                
        # 3. Compile warnings (non-blocking business warnings)
        warnings = []
        
        # Check inventory stockouts
        if inventory_rep.get("stockout_prediction"):
            for pred in inventory_rep["stockout_prediction"]:
                if pred.get("days_until_stockout", 999) < 7:
                    warnings.append({
                        "warning_code": "URGENT_STOCKOUT",
                        "warning_message": f"Product '{pred.get('product_name')}' is predicted to stock out in {pred.get('days_until_stockout')} days.",
                        "affected_agent": "inventory_agent"
                    })
                    
        # Check finance net profit
        if finance_rep.get("net_profit", 0.0) < 0.0:
            warnings.append({
                "warning_code": "NEGATIVE_NET_PROFIT",
                "warning_message": f"The business operates at a net loss of ${finance_rep.get('net_profit')}.",
                "affected_agent": "finance_agent"
            })
            
        # Check supplier high risk
        if supplier_rep.get("high_risk_suppliers"):
            warnings.append({
                "warning_code": "HIGH_RISK_SUPPLIERS",
                "warning_message": f"There are {len(supplier_rep['high_risk_suppliers'])} high-risk suppliers flagged.",
                "affected_agent": "supplier_agent"
            })
            
        # Check compliance overdue
        if compliance_rep.get("overdue_count", 0) > 0:
            warnings.append({
                "warning_code": "OVERDUE_OBLIGATIONS",
                "warning_message": f"There are {compliance_rep['overdue_count']} overdue compliance events.",
                "affected_agent": "compliance_agent"
            })
            
        # 4. Compute confidence score
        confidence_score = compute_confidence_score(validation_details)
        
        # 5. Determine validation status
        if any_failed:
            validation_status = "failed"
        elif len(warnings) > 0:
            validation_status = "passed_with_warnings"
        else:
            validation_status = "passed"
            
        # 6. Flag human review if confidence is low (<60) or validation failed
        human_review_flag = (confidence_score < 60) or (validation_status == "failed")
        
        result = {
            "agent": agent_name,
            "confidence_score": confidence_score,
            "validation_status": validation_status,
            "human_review_flag": human_review_flag,
            "validation_details": validation_details,
            "warnings": warnings
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Evaluation Agent execution failed.")
        return _error_response(agent_name, "EVALUATION_FAILED", f"Internal evaluation failure: {e}")

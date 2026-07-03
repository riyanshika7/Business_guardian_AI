from __future__ import annotations
"""Strategy Agent — converts risk scores into prioritized actions and a Business Health Score."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from google import genai
from config import GOOGLE_API_KEY, GEMINI_MODEL
from skills.business_health_skill import compute_business_health_score, prioritize_actions

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
    """Run Strategy Agent analysis.
    
    Args:
        inputs: Must contain business_risk_report, inventory_risk_report, finance_risk_report,
                supplier_risk_report, compliance_risk_report, and business_type.
    """
    agent_name = "strategy_agent"
    try:
        biz_risk_rep = inputs.get("business_risk_report")
        inventory_rep = inputs.get("inventory_risk_report")
        finance_rep = inputs.get("finance_risk_report")
        supplier_rep = inputs.get("supplier_risk_report")
        compliance_rep = inputs.get("compliance_risk_report")
        business_type = inputs.get("business_type", "retail")
        
        # 1. Validation: business risk report missing
        if biz_risk_rep is None or biz_risk_rep.get("status") == "error":
            return _error_response(agent_name, "MISSING_RISK_REPORT", "Business risk report is missing or contains errors.")
            
        # 2. Validation: domain reports check
        reports = {
            "inventory": inventory_rep,
            "finance": finance_rep,
            "supplier": supplier_rep,
            "compliance": compliance_rep
        }
        for domain, rep in reports.items():
            if rep is None:
                return _error_response(agent_name, "MISSING_DOMAIN_REPORT", f"{domain.capitalize()} risk report is missing.")
                
        # 3. Compute health score
        risk_score = biz_risk_rep.get("business_risk_score", 0)
        health_score = compute_business_health_score(risk_score)
        
        # 4. Prioritize actions
        actions = prioritize_actions(
            biz_risk_rep, inventory_rep, finance_rep, supplier_rep, compliance_rep, business_type
        )
        
        if len(actions) < 3:
            return _error_response(agent_name, "STRATEGY_GENERATION_FAILED", "Failed to generate exactly 3 prioritized action items.")
            
        # 5. Fallback rationale
        fallback_rationale = (
            "Actions are prioritized in descending order of risk severity, placing immediate focus on "
            "overdue compliance items and low inventory margins to safeguard business cash flow and operations."
        )
        rationale = fallback_rationale
        
        # 6. LLM Rationale Generation
        if GOOGLE_API_KEY:
            try:
                client = genai.Client(api_key=GOOGLE_API_KEY)
                
                prompt = (
                    f"You are a Business Strategy Consultant. Analyze this business state:\n"
                    f"- Business Health Score: {health_score}/100\n"
                    f"- Prioritized Action 1: {actions[0]['action_title']} ({actions[0]['action_description']}) - Urgency: {actions[0]['urgency']}\n"
                    f"- Prioritized Action 2: {actions[1]['action_title']} ({actions[1]['action_description']}) - Urgency: {actions[1]['urgency']}\n"
                    f"- Prioritized Action 3: {actions[2]['action_title']} ({actions[2]['action_description']}) - Urgency: {actions[2]['urgency']}\n\n"
                    f"Write a concise strategic rationale (max 2 sentences) explaining why these actions are prioritized in this order. "
                    f"Plain text only, no markdown."
                )
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                if response.text:
                    rationale = response.text.strip()
            except Exception as ex:
                logger.error(f"Gemini API call failed for Strategy Agent, using fallback: {ex}")
                
        result = {
            "agent": agent_name,
            "business_health_score": health_score,
            "priority_1_action": actions[0],
            "priority_2_action": actions[1],
            "priority_3_action": actions[2],
            "rationale": rationale
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Strategy Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")

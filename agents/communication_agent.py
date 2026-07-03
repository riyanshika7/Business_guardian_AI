from __future__ import annotations
"""Communication Agent — drafts summaries and email templates for owner review.

Enforces HITL constraints: approval_required is ALWAYS true, approval_status is ALWAYS pending on creation.
"""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from google import genai
from config import GOOGLE_API_KEY, GEMINI_MODEL

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
    """Run Communication Agent analysis.
    
    Args:
        inputs: Must contain strategy_report, business_risk_report, business_name,
                recipient_name, and communication_type. Can optionally contain
                domain reports to construct a detailed CEO briefing.
    """
    agent_name = "communication_agent"
    try:
        strategy_rep = inputs.get("strategy_report")
        biz_risk_rep = inputs.get("business_risk_report")
        business_name = inputs.get("business_name")
        recipient_name = inputs.get("recipient_name")
        comm_type = inputs.get("communication_type", "both")
        
        # Domain reports for CEO Briefing
        inv_rep = inputs.get("inventory_risk_report")
        fin_rep = inputs.get("finance_risk_report")
        sup_rep = inputs.get("supplier_risk_report")
        com_rep = inputs.get("compliance_risk_report")
        
        # 1. Validation: strategy_report check
        if strategy_rep is None or strategy_rep.get("status") == "error":
            return _error_response(agent_name, "MISSING_STRATEGY_REPORT", "Strategy report is missing or contains errors.")
            
        # 2. Validation: business_name check
        if not business_name:
            return _error_response(agent_name, "MISSING_BUSINESS_NAME", "business_name is required for personalization.")
            
        # 3. Validation: communication_type check
        if comm_type not in ["report", "email", "both"]:
            return _error_response(agent_name, "INVALID_COMMUNICATION_TYPE", "communication_type must be 'report', 'email', or 'both'.")
            
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Resolve variables needed for report / email
        health_score = strategy_rep.get("business_health_score", 0)
        risk_breakdown = biz_risk_rep.get("risk_breakdown", {}) if biz_risk_rep else {}
        risk_trend = biz_risk_rep.get("risk_trend", "stable") if biz_risk_rep else "stable"
        
        inv_score = risk_breakdown.get("inventory_risk_score", 0)
        fin_score = risk_breakdown.get("finance_risk_score", 0)
        sup_score = risk_breakdown.get("supplier_risk_score", 0)
        com_score = risk_breakdown.get("compliance_risk_score", 0)
        
        p1 = strategy_rep.get("priority_1_action", {})
        p2 = strategy_rep.get("priority_2_action", {})
        p3 = strategy_rep.get("priority_3_action", {})
        
        rec_actions = [
            p1.get("action_title", "Action 1"),
            p2.get("action_title", "Action 2"),
            p3.get("action_title", "Action 3")
        ]
        
        # 4. Generate dynamic CEO Briefing sections
        critical_issues = []
        
        # Parse Inventory stockouts
        if inv_rep and isinstance(inv_rep, dict):
            stockouts = inv_rep.get("stockout_prediction", [])
            for pred in stockouts:
                days = pred.get("days_until_stockout", 999)
                if days <= 14:
                    critical_issues.append(f"* Product {pred.get('product_name')} may stock out in {days} days")
                    
        # Parse Supplier risks
        if sup_rep and isinstance(sup_rep, dict):
            high_risk = sup_rep.get("high_risk_suppliers", [])
            for sup in high_risk:
                critical_issues.append(f"* Supplier {sup.get('supplier_name')} risk flagged: {sup.get('risk_reason')}")
                
        # Parse Compliance deadline alerts
        if com_rep and isinstance(com_rep, dict):
            alerts = com_rep.get("deadline_alerts", [])
            for alert in alerts:
                status = alert.get("status")
                days = alert.get("days_remaining", 999)
                if status == "overdue":
                    critical_issues.append(f"* Compliance event '{alert.get('event_name')}' is OVERDUE")
                elif days <= 7:
                    critical_issues.append(f"* Compliance event '{alert.get('event_name')}' due in {days} days")
                    
        # Parse Finance margins
        if fin_rep and isinstance(fin_rep, dict):
            margin = fin_rep.get("profit_margin")
            if margin is not None and margin < 10.0:
                critical_issues.append(f"* Business profit margin is low at {margin:.1f}%")
                
        # Format Recommended Actions for CEO Briefing
        briefing_actions = []
        for action_val in [p1, p2, p3]:
            title = action_val.get("action_title")
            if title:
                briefing_actions.append(f"* {title}")
                
        # Estimate Briefing Confidence
        estimated_confidence = max(60, min(99, 100 - len(critical_issues) * 4 - (100 - health_score) // 5))
        
        # Construct CEO Briefing
        ceo_briefing = (
            "Good Morning.\n\n"
            f"Business Health: {health_score}/100\n\n"
            "Critical Issues:\n" + ("\n".join(critical_issues) if critical_issues else "* No critical issues identified today.") + "\n\n"
            "Recommended Actions:\n" + ("\n".join(briefing_actions) if briefing_actions else "* No actions recommended today.") + "\n\n"
            f"Confidence: {estimated_confidence}%"
        )
        
        report_draft = None
        if comm_type in ["report", "both"]:
            # Fallback text blocks
            fallback_exec = (
                f"Executive Summary: {business_name} currently has a Business Health Score of {health_score}/100. "
                f"The business is encountering notable operational risks that demand systematic intervention. "
                f"Focusing resources on key inventory and finance optimization tasks will help secure the operational runway."
            )
            fallback_risk = (
                f"Risk Analysis: Inventory risk is {inv_score}/100, finance risk is {fin_score}/100, "
                f"supplier concentration is {sup_score}/100, and compliance exposure is {com_score}/100. "
                f"Main exposures center around immediate compliance deadlines and profit margins."
            )
            
            exec_summary = fallback_exec
            risk_summary = fallback_risk
            
            # Generate via LLM if key exists
            if GOOGLE_API_KEY:
                try:
                    client = genai.Client(api_key=GOOGLE_API_KEY)
                    
                    # Call Executive Summary
                    prompt_exec = (
                        f"You are a professional Business Communications Writer. Write a professional executive summary "
                        f"(max 3 sentences) for the business owner of '{business_name}'. The business has a Health Score of "
                        f"{health_score}/100. Highlight general health and urgency of prioritizing actions. "
                        f"Plain text only, no markdown."
                    )
                    response_exec = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_exec)
                    if response_exec.text:
                        exec_summary = response_exec.text.strip()
                        
                    # Call Risk Summary
                    prompt_risk = (
                        f"You are a Business Risk Analyst. Analyze these operational risk scores: "
                        f"Inventory Risk: {inv_score}/100, Finance Risk: {fin_score}/100, "
                        f"Supplier Risk: {sup_score}/100, Compliance Risk: {com_score}/100. "
                        f"Write a brief summary explaining these risk areas (max 3 sentences). Plain text only."
                    )
                    response_risk = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_risk)
                    if response_risk.text:
                        risk_summary = response_risk.text.strip()
                except Exception as ex:
                    logger.error(f"Gemini API call failed for Communication Agent report summaries, using fallback: {ex}")
                    
            report_draft = {
                "title": f"Business Guardian AI Report for {business_name}",
                "executive_summary": exec_summary,
                "risk_summary": risk_summary,
                "recommended_actions": rec_actions,
                "business_health_score": health_score,
                "generated_at": now_str
            }
            
        email_draft = None
        if comm_type in ["email", "both"]:
            # Rule-based email template (specifically requested by user)
            recipient = recipient_name if recipient_name else "Business Owner"
            
            email_body = (
                f"Dear {recipient},\n\n"
                f"Here is your automated operational health and risk assessment update for {business_name}.\n\n"
                f"Business Health Score: {health_score}/100\n"
                f"Overall Risk Trend: {risk_trend.upper()}\n\n"
                f"Prioritized Action Items for this period:\n"
                f"1. [URGENCY: {p1.get('urgency', 'immediate').upper()}] {p1.get('action_title')}\n"
                f"   Description: {p1.get('action_description')}\n"
                f"   Expected Impact: {p1.get('expected_impact')}\n\n"
                f"2. [URGENCY: {p2.get('urgency', 'this_week').upper()}] {p2.get('action_title')}\n"
                f"   Description: {p2.get('action_description')}\n"
                f"   Expected Impact: {p2.get('expected_impact')}\n\n"
                f"3. [URGENCY: {p3.get('urgency', 'this_month').upper()}] {p3.get('action_title')}\n"
                f"   Description: {p3.get('action_description')}\n"
                f"   Expected Impact: {p3.get('expected_impact')}\n\n"
                f"This draft has been prepared by Business Guardian AI. External sending requires your explicit review "
                f"and approval on the dashboard.\n\n"
                f"Best regards,\n"
                f"Business Guardian AI System"
            )
            
            email_draft = {
                "subject": f"Operational Risk Assessment Update — {business_name}",
                "recipient_name": recipient,
                "body": email_body,
                "generated_at": now_str
            }
            
        result = {
            "agent": agent_name,
            "report_draft": report_draft,
            "email_draft": email_draft,
            "ceo_briefing": ceo_briefing,
            "approval_required": True,
            "approval_status": "pending"
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Communication Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")

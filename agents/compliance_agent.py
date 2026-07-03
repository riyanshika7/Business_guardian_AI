from __future__ import annotations
"""Compliance Agent — tracks compliance deadlines and obligation dates to prevent lapses."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any
import re

# Ensure project root is in sys.path so config and other modules can be imported when running directly
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from skills.forecasting_skill import compute_compliance_risk_score

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
    """Run Compliance Agent analysis.
    
    Args:
        inputs: Must contain compliance_events, calendar_events, analysis_window_days, and business_type.
    """
    agent_name = "compliance_agent"
    try:
        compliance_events = inputs.get("compliance_events")
        calendar_events = inputs.get("calendar_events", [])
        analysis_window_days = inputs.get("analysis_window_days", 30)
        
        # 1. Validation: compliance_events is missing
        if compliance_events is None:
            return _error_response(agent_name, "MISSING_COMPLIANCE_DATA", "Compliance events list is missing.")
            
        # 2. Validation: analysis_window_days range check
        try:
            analysis_window_days = int(analysis_window_days)
            if analysis_window_days <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return _error_response(agent_name, "INVALID_ANALYSIS_WINDOW", "Analysis window must be a positive integer.")
            
        # 3. Validation: Date formats
        date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}")
        
        for idx, ev in enumerate(compliance_events):
            due = ev.get("due_date", "")
            if not due or not date_regex.match(due):
                return _error_response(agent_name, "INVALID_DATE_FORMAT", f"Compliance event at index {idx} has invalid due_date format.")
                
        for idx, ev in enumerate(calendar_events):
            due = ev.get("due_date", "")
            if not due or not date_regex.match(due):
                return _error_response(agent_name, "INVALID_DATE_FORMAT", f"Calendar event at index {idx} has invalid due_date format.")
                
        # 4. Merge Events and Deduplicate by event_id
        merged_map = {}
        for ev in compliance_events:
            e_id = ev.get("event_id")
            if e_id:
                merged_map[e_id] = ev
                
        for ev in calendar_events:
            e_id = ev.get("event_id")
            if e_id:
                # Calendar events overwrite or add
                merged_map[e_id] = ev
                
        merged_events = list(merged_map.values())
        
        # 5. Process Deadlines
        # Dynamically resolve current date with override options for testing
        import os
        current_date_str = inputs.get("current_date")
        if current_date_str:
            try:
                current_date_obj = datetime.strptime(current_date_str.split("T")[0], "%Y-%m-%d").date()
            except ValueError:
                current_date_obj = date.today()
        else:
            env_date = os.getenv("CURRENT_DATE_OVERRIDE")
            if env_date:
                try:
                    current_date_obj = datetime.strptime(env_date, "%Y-%m-%d").date()
                except ValueError:
                    current_date_obj = date.today()
            else:
                current_date_obj = date.today()
        
        deadline_alerts = []
        overdue_count = 0
        due_soon_count = 0
        
        for ev in merged_events:
            due_str = ev.get("due_date", "")
            # Extract YYYY-MM-DD
            due_date_str = due_str.split("T")[0] if "T" in due_str else due_str
            
            try:
                due_date_obj = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
                
            days_remaining = (due_date_obj - current_date_obj).days
            
            # Categorize status & severity
            if days_remaining < 0:
                status = "overdue"
                severity = "critical"
                overdue_count += 1
            elif days_remaining <= analysis_window_days:
                status = "due_soon"
                severity = "high" if days_remaining <= 7 else "medium"
                due_soon_count += 1
            else:
                status = "upcoming"
                severity = "low"
                
            deadline_alerts.append({
                "event_id": ev.get("event_id", ""),
                "event_name": ev.get("event_name", "Unknown Event"),
                "due_date": due_date_str,
                "days_remaining": days_remaining,
                "status": status,
                "severity": severity
            })
            
        # 6. Compute compliance risk score
        risk_score = compute_compliance_risk_score(overdue_count, due_soon_count, len(merged_events))
        
        # 7. Rule-based recommendation
        if overdue_count > 0:
            recommendation = f"Urgent action required: {overdue_count} compliance obligations are overdue. Resolve immediately to prevent legal penalties."
        elif due_soon_count > 0:
            recommendation = f"Monitor compliance calendar: {due_soon_count} tasks are due soon within the next {analysis_window_days} days. Assign owners to prevent lapses."
        else:
            recommendation = "All compliance obligations are up-to-date. Continue tracking calendar milestones."
            
        result = {
            "agent": agent_name,
            "compliance_risk_score": risk_score,
            "deadline_alerts": deadline_alerts,
            "compliance_recommendation": recommendation,
            "overdue_count": overdue_count,
            "due_soon_count": due_soon_count
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Compliance Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")

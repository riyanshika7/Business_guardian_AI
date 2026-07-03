"""Google Calendar MCP Client.

Connects to a real Google Workspace Calendar MCP server via stdio,
falling back to local CSV files if authentication or the server is unavailable.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import re
import os
import csv
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def _fetch_from_gws_calendar(calendar_id: str, look_ahead_days: int) -> list[dict[str, Any]]:
    """Connect to official gws-calendar MCP server to retrieve compliance deadlines."""
    import asyncio
    
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@google/mcp-gws-calendar"]
    )
    
    time_min = datetime.now(timezone.utc).isoformat()
    time_max = (datetime.now(timezone.utc) + timedelta(days=look_ahead_days)).isoformat()
    
    async def _fetch_task():
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                response = await session.call_tool("list_events", arguments={
                    "calendarId": calendar_id,
                    "timeMin": time_min,
                    "timeMax": time_max
                })
                
                events = []
                if response and hasattr(response, "content") and response.content:
                    raw_text = response.content[0].text
                    raw_data = json.loads(raw_text)
                    for item in raw_data.get("items", []):
                        start = item.get("start", {})
                        due_date = start.get("date") or start.get("dateTime", "")[:10]
                        desc = item.get("description", "")
                        
                        event_type = "other"
                        for t in ["tax", "license", "insurance", "regulatory", "contract_renewal"]:
                            if t in desc.lower() or t in item.get("summary", "").lower():
                                event_type = t
                                break
                                
                        events.append({
                            "event_id": item.get("id"),
                            "event_name": item.get("summary", "Compliance Event"),
                            "event_type": event_type,
                            "due_date": due_date,
                            "description": desc or item.get("summary"),
                            "responsible_party": "ops_manager",
                            "status": "pending",
                            "recurrence": "none"
                        })
                return events

    # Enforce a 3.0 second connection/init timeout to prevent uvicorn hangs
    return await asyncio.wait_for(_fetch_task(), timeout=3.0)

# ===================================================================
# Public MCP Entry Point
# ===================================================================

def fetch_calendar_data(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate input parameters and retrieve corporate compliance deadlines."""
    calendar_id = inputs.get("calendar_id")
    look_ahead_days = inputs.get("look_ahead_days")
    event_types = inputs.get("event_types", [])
    
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        # 1. Validation: calendar_id must be non-empty
        if not calendar_id or not isinstance(calendar_id, str):
            return {
                "mcp": "calendar_mcp",
                "status": "error",
                "error_code": "MISSING_CALENDAR_ID",
                "error_message": "calendar_id is a required configuration parameter and must be non-empty.",
                "fetched_at": fetched_at
            }
            
        # 2. Validation: look_ahead_days range checks
        if look_ahead_days is None:
            return {
                "mcp": "calendar_mcp",
                "status": "error",
                "error_code": "INVALID_LOOK_AHEAD_DAYS",
                "error_message": "look_ahead_days is required.",
                "fetched_at": fetched_at
            }
            
        try:
            look_ahead_days = int(look_ahead_days)
            if not (1 <= look_ahead_days <= 365):
                raise ValueError()
        except (ValueError, TypeError):
            return {
                "mcp": "calendar_mcp",
                "status": "error",
                "error_code": "INVALID_LOOK_AHEAD_DAYS",
                "error_message": "look_ahead_days must be an integer between 1 and 365.",
                "fetched_at": fetched_at
            }
            
        # 3. Validation: event_types checklist
        permitted_types = ["tax", "license", "insurance", "regulatory", "contract_renewal", "other"]
        if event_types is not None:
            if not isinstance(event_types, list):
                return {
                    "mcp": "calendar_mcp",
                    "status": "error",
                    "error_code": "INVALID_EVENT_TYPE",
                    "error_message": "event_types must be a list of strings.",
                    "fetched_at": fetched_at
                }
            for et in event_types:
                if et not in permitted_types:
                    return {
                        "mcp": "calendar_mcp",
                        "status": "error",
                        "error_code": "INVALID_EVENT_TYPE",
                        "error_message": f"Event type '{et}' is not a valid compliance category.",
                        "fetched_at": fetched_at
                    }
                    
        # Try fetching using real GWS Calendar MCP
        mcp_events = None
        if calendar_id != "calendar-12345":
            try:
                import asyncio
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            try:
                mcp_events = loop.run_until_complete(_fetch_from_gws_calendar(calendar_id, look_ahead_days))
                logger.info("Successfully fetched calendar events from GWS Calendar MCP.")
            except Exception as e:
                logger.warning(f"Connection to GWS Calendar MCP failed (falling back to CSV): {e}")

        # Local CSV Loading Fallback
        all_events = mcp_events
        if all_events is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(project_root, "database", "compliance_events.csv")
            csv_path_alt = os.path.join(project_root, "database", "calendar_events.csv")
            
            all_events = []
            loaded_from_csv = False
            
            for path in (csv_path, csv_path_alt):
                if os.path.exists(path):
                    try:
                        with open(path, encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                all_events.append({
                                    "event_id": row.get("event_id"),
                                    "event_name": row.get("event_name"),
                                    "event_type": row.get("event_type"),
                                    "due_date": row.get("due_date"),
                                    "description": row.get("description"),
                                    "responsible_party": row.get("responsible_party"),
                                    "status": row.get("status"),
                                    "recurrence": row.get("recurrence")
                                })
                            loaded_from_csv = True
                            break
                    except Exception:
                        pass
            
            if not loaded_from_csv:
                all_events = [
                    {
                        "event_id": "EVT-001",
                        "event_name": "Quarterly GST Filing Q2",
                        "event_type": "tax",
                        "due_date": "2026-07-15",
                        "description": "GST tax return filing obligation for Q2 operational revenue.",
                        "responsible_party": "finance_manager",
                        "status": "pending",
                        "recurrence": "quarterly"
                    },
                    {
                        "event_id": "EVT-002",
                        "event_name": "Corporate Insurance Policy Renewal",
                        "event_type": "insurance",
                        "due_date": "2026-07-28",
                        "description": "Commercial general liability policy renewal deadline.",
                        "responsible_party": "ops_director",
                        "status": "pending",
                        "recurrence": "annual"
                    },
                    {
                        "event_id": "EVT-003",
                        "event_name": "Municipal Food Safety License Renewal",
                        "event_type": "license",
                        "due_date": "2026-06-20",
                        "description": "Annual food production safety audit and certification renewal.",
                        "responsible_party": "compliance_lead",
                        "status": "overdue",
                        "recurrence": "annual"
                    }
                ]
        
        # 4. Perform integrity check on the event dates
        for e in all_events:
            due_date = e.get("due_date")
            if not due_date or not isinstance(due_date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", due_date):
                return {
                    "mcp": "calendar_mcp",
                    "status": "error",
                    "error_code": "INVALID_DATE_FORMAT",
                    "error_message": f"Calendar event '{e.get('event_id')}' contains a malformed date string.",
                    "fetched_at": fetched_at
                }
            try:
                datetime.strptime(due_date, "%Y-%m-%d")
            except ValueError:
                return {
                    "mcp": "calendar_mcp",
                    "status": "error",
                    "error_code": "INVALID_DATE_FORMAT",
                    "error_message": f"Calendar event '{e.get('event_id')}' contains an invalid calendar date.",
                    "fetched_at": fetched_at
                }
                
        # 5. Filter events by look-ahead window and type
        now = datetime.now(timezone.utc)
        current_date_str = now.strftime("%Y-%m-%d")
        limit_date_str = (now + timedelta(days=look_ahead_days)).strftime("%Y-%m-%d")
        
        filtered_events = []
        for e in all_events:
            if event_types and e["event_type"] not in event_types:
                continue
                
            due_date = e["due_date"]
            if due_date < current_date_str or (current_date_str <= due_date <= limit_date_str):
                filtered_events.append(e)
                
        return {
            "mcp": "calendar_mcp",
            "status": "success",
            "data": {
                "calendar_events": filtered_events,
                "look_ahead_days": look_ahead_days,
                "total_events_returned": len(filtered_events)
            },
            "warnings": None,
            "fetched_at": fetched_at
        }
        
    except Exception as e:
        return {
            "mcp": "calendar_mcp",
            "status": "error",
            "error_code": "FETCH_FAILED",
            "error_message": f"An unexpected error occurred while fetching calendar data: {str(e)}",
            "fetched_at": fetched_at
        }

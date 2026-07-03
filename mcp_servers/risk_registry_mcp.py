"""Risk Registry MCP Server & Client.

Exposes a custom FastMCP server when run directly as a script, and acts
as a client wrapper when imported by the agent layers.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
import re
import logging
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP("Risk Registry")

logger = logging.getLogger(__name__)

# ===================================================================
# FastMCP Tools
# ===================================================================

@mcp_server.tool()
def get_risk_history_records() -> list[dict[str, Any]]:
    """Retrieve all historical risk score entries."""
    now = datetime.now(timezone.utc)
    return [
        {
            "score_id": "HIS-001",
            "agent_name": "risk_tracker_agent",
            "score_type": "business_risk",
            "score_value": 45,
            "run_id": "run-uuid-101",
            "recorded_at": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "score_id": "HIS-002",
            "agent_name": "risk_tracker_agent",
            "score_type": "business_risk",
            "score_value": 47,
            "run_id": "run-uuid-102",
            "recorded_at": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "score_id": "HIS-003",
            "agent_name": "risk_tracker_agent",
            "score_type": "business_risk",
            "score_value": 50,
            "run_id": "run-uuid-103",
            "recorded_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "score_id": "HIS-004",
            "agent_name": "inventory_agent",
            "score_type": "inventory_risk",
            "score_value": 60,
            "run_id": "run-uuid-103",
            "recorded_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "score_id": "HIS-005",
            "agent_name": "finance_agent",
            "score_type": "finance_risk",
            "score_value": 35,
            "run_id": "run-uuid-103",
            "recorded_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "score_id": "HIS-006",
            "agent_name": "supplier_agent",
            "score_type": "supplier_risk",
            "score_value": 55,
            "run_id": "run-uuid-103",
            "recorded_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "score_id": "HIS-007",
            "agent_name": "compliance_agent",
            "score_type": "compliance_risk",
            "score_value": 40,
            "run_id": "run-uuid-103",
            "recorded_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    ]

# ===================================================================
# Helper validation
# ===================================================================

def _is_valid_timestamp(ts_str: Any) -> bool:
    if not isinstance(ts_str, str):
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts_str):
        return False
    try:
        datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False

# ===================================================================
# Public MCP Client Entry Point
# ===================================================================

def fetch_risk_history(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate query terms and retrieve risk score history and trends."""
    business_id = inputs.get("business_id")
    score_types = inputs.get("score_types")
    history_days = inputs.get("history_days", 90)
    
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        # 1. Validation: business_id must be non-empty
        if not business_id or not isinstance(business_id, str):
            return {
                "mcp": "risk_registry_mcp",
                "status": "error",
                "error_code": "MISSING_BUSINESS_ID",
                "error_message": "business_id is a required search parameter and must be non-empty.",
                "fetched_at": fetched_at
            }
            
        # Simulate missing business check
        if business_id == "missing-business-uuid":
            return {
                "mcp": "risk_registry_mcp",
                "status": "error",
                "error_code": "BUSINESS_NOT_FOUND",
                "error_message": f"No business entity registered under specified UUID: {business_id}.",
                "fetched_at": fetched_at
            }
            
        # 2. Validation: history_days checks
        try:
            history_days = int(history_days)
            if not (1 <= history_days <= 365):
                raise ValueError()
        except (ValueError, TypeError):
            return {
                "mcp": "risk_registry_mcp",
                "status": "error",
                "error_code": "INVALID_HISTORY_DAYS",
                "error_message": "history_days must be an integer between 1 and 365.",
                "fetched_at": fetched_at
            }
            
        # 3. Validation: score_types checks
        permitted_types = [
            "inventory_risk",
            "finance_risk",
            "supplier_risk",
            "compliance_risk",
            "business_risk",
            "business_health",
            "confidence"
        ]
        
        if score_types is not None:
            if not isinstance(score_types, list):
                return {
                    "mcp": "risk_registry_mcp",
                    "status": "error",
                    "error_code": "INVALID_SCORE_TYPE",
                    "error_message": "score_types must be a list of strings.",
                    "fetched_at": fetched_at
                }
            for st in score_types:
                if st not in permitted_types:
                    return {
                        "mcp": "risk_registry_mcp",
                        "status": "error",
                        "error_code": "INVALID_SCORE_TYPE",
                        "error_message": f"Score type '{st}' is not a valid registry category.",
                        "fetched_at": fetched_at
                    }
                    
        now = datetime.now(timezone.utc)
        
        # Resolve history using custom MCP tool function locally
        mock_history = get_risk_history_records()
        
        # 4. Perform integrity check on mock data timestamps
        for record in mock_history:
            if not _is_valid_timestamp(record["recorded_at"]):
                raise ValueError("Record recorded_at violates ISO 8601 formatting rules.")
                
        # 5. Filter history by score types and history days
        limit_date = now - timedelta(days=history_days)
        filtered_history = []
        for record in mock_history:
            if score_types and record["score_type"] not in score_types:
                continue
            rec_dt = datetime.strptime(record["recorded_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if rec_dt >= limit_date:
                filtered_history.append(record)
                
        # 6. Calculate risk_status dynamically
        biz_risk_records = [r for r in filtered_history if r["score_type"] == "business_risk"]
        biz_risk_records.sort(key=lambda x: x["recorded_at"], reverse=True)
        
        risk_status = {
            "current_business_risk_score": None,
            "last_run_id": None,
            "last_run_timestamp": None
        }
        if biz_risk_records:
            latest_biz_risk = biz_risk_records[0]
            risk_status = {
                "current_business_risk_score": latest_biz_risk["score_value"],
                "last_run_id": latest_biz_risk["run_id"],
                "last_run_timestamp": latest_biz_risk["recorded_at"]
            }
            
        # 7. Calculate risk_scores statistics dynamically
        grouped_records: dict[str, list[dict[str, Any]]] = {}
        for r in filtered_history:
            grouped_records.setdefault(r["score_type"], []).append(r)
            
        risk_scores = []
        for s_type, recs in grouped_records.items():
            recs.sort(key=lambda x: x["recorded_at"], reverse=True)
            values = [x["score_value"] for x in recs]
            risk_scores.append({
                "score_type": s_type,
                "latest_value": recs[0]["score_value"],
                "average_value": round(sum(values) / len(values), 2),
                "min_value": min(values),
                "max_value": max(values),
                "data_points": len(recs)
            })
            
        # 8. Calculate risk_trends dynamically
        risk_trends = []
        for s_type, recs in grouped_records.items():
            recs.sort(key=lambda x: x["recorded_at"])  # Sort oldest to newest
            if len(recs) < 2:
                trend_dir = "stable"
            else:
                oldest_val = recs[0]["score_value"]
                latest_val = recs[-1]["score_value"]
                
                if latest_val > oldest_val:
                    if s_type in ["business_health", "confidence"]:
                        trend_dir = "improving"
                    else:
                        trend_dir = "deteriorating"
                elif latest_val < oldest_val:
                    if s_type in ["business_health", "confidence"]:
                        trend_dir = "deteriorating"
                    else:
                        trend_dir = "improving"
                else:
                    trend_dir = "stable"
                    
            risk_trends.append({
                "score_type": s_type,
                "trend_direction": trend_dir,
                "trend_confidence": 0.85,
                "period_days": history_days
            })
            
        return {
            "mcp": "risk_registry_mcp",
            "status": "success",
            "data": {
                "risk_history": filtered_history,
                "risk_status": risk_status,
                "risk_scores": risk_scores,
                "risk_trends": risk_trends,
                "history_days": history_days,
                "total_records_returned": len(filtered_history)
            },
            "warnings": None,
            "fetched_at": fetched_at
        }
        
    except ValueError as ve:
        return {
            "mcp": "risk_registry_mcp",
            "status": "error",
            "error_code": "DATABASE_QUERY_ERROR",
            "error_message": f"Database / registry format corruption: {str(ve)}",
            "fetched_at": fetched_at
        }
    except Exception as e:
        return {
            "mcp": "risk_registry_mcp",
            "status": "error",
            "error_code": "DATABASE_QUERY_ERROR",
            "error_message": f"Registry database query failure: {str(e)}",
            "fetched_at": fetched_at
        }

if __name__ == "__main__":
    import sys
    try:
        if sys.stdin.isatty():
            mcp_server.settings.port = 8001
            
            # Add custom Starlette routes to handle root (/) and favicon.ico gracefully for browsers/judges
            from starlette.routing import Route
            from starlette.responses import HTMLResponse, Response
            
            async def root_handler(request):
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Risk Registry MCP Server</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                            background: radial-gradient(circle at top, #1e293b, #0f172a);
                            color: #f8fafc;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                        }
                        .card {
                            text-align: center;
                            padding: 3rem;
                            background: rgba(30, 41, 59, 0.7);
                            backdrop-filter: blur(12px);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 16px;
                            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
                            max-width: 550px;
                        }
                        .icon {
                            font-size: 4rem;
                            margin-bottom: 1.5rem;
                            display: inline-block;
                        }
                        h1 {
                            font-size: 2rem;
                            margin: 0 0 1rem 0;
                            background: linear-gradient(135deg, #38bdf8, #818cf8);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                        }
                        p {
                            font-size: 1.1rem;
                            line-height: 1.6;
                            color: #94a3b8;
                            margin: 0 0 2rem 0;
                        }
                        .btn {
                            display: inline-block;
                            padding: 0.75rem 1.5rem;
                            background: linear-gradient(135deg, #0284c7, #4f46e5);
                            color: #ffffff;
                            text-decoration: none;
                            border-radius: 8px;
                            font-weight: 600;
                            transition: transform 0.2s, box-shadow 0.2s;
                        }
                        .btn:hover {
                            transform: translateY(-2px);
                            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
                        }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <span class="icon">🛡️</span>
                        <h1>Risk Registry MCP Server</h1>
                        <p>This is a Model Context Protocol (MCP) server endpoint running on SSE transport for the Business Guardian AI pipeline. It does not host a user interface directly.</p>
                        <a class="btn" href="http://localhost:5173/">Go to Business Dashboard</a>
                    </div>
                </body>
                </html>
                """
                return HTMLResponse(html)

            async def favicon_handler(request):
                return Response(status_code=204)

            mcp_server._custom_starlette_routes.extend([
                Route("/", root_handler, methods=["GET"]),
                Route("/favicon.ico", favicon_handler, methods=["GET"]),
            ])

            print("----------------------------------------------------------------------")
            print("Risk Registry MCP Server running in interactive terminal mode.")
            print("Note: In production/testing, this runs in stdio mode via subprocess.")
            print("Launching in SSE web server mode on http://127.0.0.1:8001 ...")
            print("Press Ctrl+C to stop.")
            print("----------------------------------------------------------------------")
            mcp_server.run(transport="sse")
        else:
            mcp_server.run(transport="stdio")
    except KeyboardInterrupt:
        print("\n[INFO] Risk Registry MCP Server stopped gracefully.")
        sys.exit(0)

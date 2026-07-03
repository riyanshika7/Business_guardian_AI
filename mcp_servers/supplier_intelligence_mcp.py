"""Supplier Intelligence MCP Server & Client.

Exposes a custom FastMCP server when run directly as a script, and acts
as a client wrapper when imported by the agent layers.
"""

from __future__ import annotations
from datetime import datetime, timezone
import re
import logging
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP("Supplier Intelligence")

logger = logging.getLogger(__name__)

# ===================================================================
# Mock Databases
# ===================================================================

PROFILES_DB = {
    "SUP-001": {
        "supplier_id": "SUP-001",
        "supplier_name": "Alpha Supplies",
        "country": "USA",
        "product_categories": ["electronics", "office_supplies"],
        "reliability_score": 85,
        "quality_score": 92,
        "delivery_performance": {
            "on_time_rate_percent": 90.5,
            "average_delay_days": 1.2
        },
        "financial_stability_indicator": "stable",
        "active_since": "2023-01-15",
        "contract_end_date": "2026-12-31",
        "risk_flags": []
    },
    "SUP-002": {
        "supplier_id": "SUP-002",
        "supplier_name": "Beta Logistics",
        "country": "Canada",
        "product_categories": ["packaging", "delivery_services"],
        "reliability_score": 58,  # Underperforming
        "quality_score": 75,
        "delivery_performance": {
            "on_time_rate_percent": 68.0,
            "average_delay_days": 4.5
        },
        "financial_stability_indicator": "watch",
        "active_since": "2024-03-10",
        "contract_end_date": "2026-11-30",
        "risk_flags": ["high_delay_rate", "financial_stability_watch"]
    }
}

HISTORY_DB = {
    "SUP-001": [
        {
            "supplier_id": "SUP-001",
            "month": "2026-05",
            "orders_placed": 10,
            "orders_fulfilled": 10,
            "fulfilment_rate_percent": 100.0,
            "incidents": []
        },
        {
            "supplier_id": "SUP-001",
            "month": "2026-04",
            "orders_placed": 12,
            "orders_fulfilled": 11,
            "fulfilment_rate_percent": 91.6,
            "incidents": ["Damaged packaging on 1 parcel"]
        }
    ],
    "SUP-002": [
        {
            "supplier_id": "SUP-002",
            "month": "2026-05",
            "orders_placed": 15,
            "orders_fulfilled": 10,
            "fulfilment_rate_percent": 66.6,
            "incidents": ["Late delivery - 5 days delay"]
        },
        {
            "supplier_id": "SUP-002",
            "month": "2026-04",
            "orders_placed": 8,
            "orders_fulfilled": 5,
            "fulfilment_rate_percent": 62.5,
            "incidents": ["Incorrect items sent in order"]
        }
    ]
}

RISK_DB = {
    "SUP-001": {
        "supplier_id": "SUP-001",
        "risk_score": 15,
        "risk_level": "low",
        "primary_risk_factor": "none",
        "last_assessed": "2026-06-01"
    },
    "SUP-002": {
        "supplier_id": "SUP-002",
        "risk_score": 75,
        "risk_level": "high",
        "primary_risk_factor": "Fulfillment failure and high delays",
        "last_assessed": "2026-06-20"
    }
}

# ===================================================================
# FastMCP Tools
# ===================================================================

@mcp_server.tool()
def get_supplier_profile(supplier_id: str) -> dict[str, Any] | None:
    """Retrieve detailed contract profile for a supplier by ID."""
    return PROFILES_DB.get(supplier_id)

@mcp_server.tool()
def get_supplier_history(supplier_id: str) -> list[dict[str, Any]]:
    """Retrieve delivery history records for a supplier by ID."""
    return HISTORY_DB.get(supplier_id, [])

@mcp_server.tool()
def get_supplier_risk_data(supplier_id: str) -> dict[str, Any] | None:
    """Retrieve active risk levels and assessments for a supplier by ID."""
    return RISK_DB.get(supplier_id)

# ===================================================================
# Helper validation
# ===================================================================

def _is_valid_date(date_str: Any) -> bool:
    if not isinstance(date_str, str):
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def _is_valid_month(month_str: Any) -> bool:
    if not isinstance(month_str, str):
        return False
    if not re.match(r"^\d{4}-\d{2}$", month_str):
        return False
    try:
        datetime.strptime(month_str, "%Y-%m")
        return True
    except ValueError:
        return False

# ===================================================================
# Public MCP Client Entry Point
# ===================================================================

def fetch_supplier_intelligence(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate supplier IDs and fetch delivery performance, profiles, and risk markers."""
    supplier_ids = inputs.get("supplier_ids", [])
    include_history = inputs.get("include_history", True)
    history_months = inputs.get("history_months", 6)
    
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        # 1. Validation: supplier_ids array checks
        if not supplier_ids or not isinstance(supplier_ids, list):
            return {
                "mcp": "supplier_intelligence_mcp",
                "status": "error",
                "error_code": "MISSING_SUPPLIER_IDS",
                "error_message": "supplier_ids list must be provided and must be non-empty.",
                "fetched_at": fetched_at
            }
            
        for s_id in supplier_ids:
            if not isinstance(s_id, str) or not s_id:
                return {
                    "mcp": "supplier_intelligence_mcp",
                    "status": "error",
                    "error_code": "MISSING_SUPPLIER_IDS",
                    "error_message": "supplier_ids must contain only non-empty strings.",
                    "fetched_at": fetched_at
                }
                
        # 2. Validation: history_months checks
        try:
            history_months = int(history_months)
            if not (1 <= history_months <= 24):
                raise ValueError()
        except (ValueError, TypeError):
            return {
                "mcp": "supplier_intelligence_mcp",
                "status": "error",
                "error_code": "INVALID_HISTORY_MONTHS",
                "error_message": "history_months must be an integer between 1 and 24.",
                "fetched_at": fetched_at
            }
            
        # 3. Perform domain checks on mock database content before returning
        permitted_indicators = ["stable", "watch", "at_risk"]
        permitted_levels = ["high", "medium", "low"]
        
        for key, p in PROFILES_DB.items():
            if not _is_valid_date(p["active_since"]):
                raise ValueError(f"Supplier {key} contains invalid active_since date.")
            if p["contract_end_date"] is not None and not _is_valid_date(p["contract_end_date"]):
                raise ValueError(f"Supplier {key} contains invalid contract_end_date.")
            if p["financial_stability_indicator"] not in permitted_indicators:
                raise ValueError(f"Supplier {key} contains invalid stability indicator.")
            if not (0 <= p["reliability_score"] <= 100) or not (0 <= p["quality_score"] <= 100):
                raise ValueError(f"Supplier {key} contains score out of range.")
                
        for key, hist in HISTORY_DB.items():
            for entry in hist:
                if not _is_valid_month(entry["month"]):
                    raise ValueError(f"Supplier history entry for {key} has invalid month format.")
                    
        for key, r in RISK_DB.items():
            if not _is_valid_date(r["last_assessed"]):
                raise ValueError(f"Supplier risk data for {key} has invalid last_assessed date.")
            if r["risk_level"] not in permitted_levels:
                raise ValueError(f"Supplier risk data for {key} has invalid risk level.")
            if not (0 <= r["risk_score"] <= 100):
                raise ValueError(f"Supplier risk data for {key} has risk score out of range.")
                
        # Resolve requested suppliers using FastMCP tool functions locally
        supplier_profiles = []
        supplier_history = []
        supplier_risk_data = []
        warnings = []
        
        for s_id in supplier_ids:
            profile = get_supplier_profile(s_id)
            if profile:
                supplier_profiles.append(profile)
                if include_history:
                    history = get_supplier_history(s_id)
                    supplier_history.extend(history[:history_months])
                risk = get_supplier_risk_data(s_id)
                if risk:
                    supplier_risk_data.append(risk)
            else:
                warnings.append(f"Supplier ID '{s_id}' not found in intelligence database.")
                
        if not supplier_profiles:
            return {
                "mcp": "supplier_intelligence_mcp",
                "status": "error",
                "error_code": "NO_SUPPLIERS_FOUND",
                "error_message": "Zero requested supplier IDs resolved in the intelligence database.",
                "fetched_at": fetched_at
            }
            
        return {
            "mcp": "supplier_intelligence_mcp",
            "status": "success",
            "data": {
                "supplier_profiles": supplier_profiles,
                "supplier_history": supplier_history,
                "supplier_risk_data": supplier_risk_data,
                "total_suppliers_returned": len(supplier_profiles)
            },
            "warnings": warnings if warnings else None,
            "fetched_at": fetched_at
        }
        
    except ValueError as ve:
        return {
            "mcp": "supplier_intelligence_mcp",
            "status": "error",
            "error_code": "CORRUPTED_PAYLOAD_ERROR",
            "error_message": f"Database payload error: {str(ve)}",
            "fetched_at": fetched_at
        }
    except Exception as e:
        return {
            "mcp": "supplier_intelligence_mcp",
            "status": "error",
            "error_code": "UPSTREAM_API_TIMEOUT",
            "error_message": f"An unexpected error occurred while fetching supplier intelligence: {str(e)}",
            "fetched_at": fetched_at
        }

if __name__ == "__main__":
    import sys
    try:
        if sys.stdin.isatty():
            mcp_server.settings.port = 8002
            
            # Add custom Starlette routes to handle root (/) and favicon.ico gracefully for browsers/judges
            from starlette.routing import Route
            from starlette.responses import HTMLResponse, Response
            
            async def root_handler(request):
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Supplier Intelligence MCP Server</title>
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
                        <span class="icon">🤝</span>
                        <h1>Supplier Intelligence MCP Server</h1>
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
            print("Supplier Intelligence MCP Server running in interactive terminal mode.")
            print("Note: In production/testing, this runs in stdio mode via subprocess.")
            print("Launching in SSE web server mode on http://127.0.0.1:8002 ...")
            print("Press Ctrl+C to stop.")
            print("----------------------------------------------------------------------")
            mcp_server.run(transport="sse")
        else:
            mcp_server.run(transport="stdio")
    except KeyboardInterrupt:
        print("\n[INFO] Supplier Intelligence MCP Server stopped gracefully.")
        sys.exit(0)

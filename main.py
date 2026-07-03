"""Main entrypoint for the FastAPI backend of Business Guardian AI."""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from pydantic import BaseModel, Field
from database import db
from Orchestrator import orchestrator
from config import API_SECURITY_KEY

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key", description="API Security Key")):
    if x_api_key != API_SECURITY_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyzeRequest(BaseModel):
    """Request model for starting analysis."""
    business_id: str
    business_name: str
    business_type: str = Field(description="retail | agriculture | ecommerce")
    period_days: int = Field(gt=0, default=30)
    analysis_window_days: int = Field(gt=0, default=30)
    communication_type: str = Field(default="both", description="report | email | both")
    recipient_name: str | None = Field(default=None)

class ApproveRequest(BaseModel):
    """Request model for resuming analysis after HITL gate."""
    run_id: str
    approval_status: str = Field(description="approved | rejected")

def pre_populate_database() -> None:
    """Pre-populate products and compliance events if empty."""
    import os
    import csv
    from datetime import datetime, timezone
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Check if products table is empty
        prod_count = db.fetch_one("SELECT COUNT(*) as count FROM products")
        if prod_count and prod_count["count"] == 0:
            logger.info("Pre-populating products catalog...")
            csv_path = os.path.join(project_root, "database", "products.csv")
            loaded_from_csv = False
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            db.insert_row("products", {
                                "product_id": row.get("product_id"),
                                "product_name": row.get("product_name"),
                                "category": row.get("category"),
                                "sku": row.get("sku"),
                                "unit_cost": float(row.get("unit_cost", 0.0)),
                                "unit_price": float(row.get("unit_price", 0.0)),
                                "reorder_point": int(row.get("reorder_point", 0)),
                                "reorder_quantity": int(row.get("reorder_quantity", 0)),
                                "supplier_id": row.get("supplier_id"),
                                "is_active": 1 if row.get("is_active", "True").lower() in ("true", "1", "yes") else 0,
                                "created_at": row.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                            })
                    loaded_from_csv = True
                    logger.info("Products pre-populated from CSV.")
                except Exception as ex:
                    logger.error(f"Failed to load products from CSV: {ex}")
            
            if not loaded_from_csv:
                # SUP-001 products
                db.insert_row("products", {
                    "product_id": "PROD-001",
                    "product_name": "Eco Widget A",
                    "category": "electronics",
                    "sku": "ECO-WID-A",
                    "unit_cost": 10.0,
                    "unit_price": 20.0,
                    "reorder_point": 25,
                    "reorder_quantity": 50,
                    "supplier_id": "SUP-001",
                    "is_active": 1,
                    "created_at": "2026-01-01T00:00:00Z"
                })
                # SUP-002 products
                db.insert_row("products", {
                    "product_id": "PROD-002",
                    "product_name": "Premium Widget B",
                    "category": "electronics",
                    "sku": "ECO-WID-B",
                    "unit_cost": 5.0,
                    "unit_price": 15.0,
                    "reorder_point": 5,
                    "reorder_quantity": 20,
                    "supplier_id": "SUP-002",
                    "is_active": 1,
                    "created_at": "2026-01-01T00:00:00Z"
                })
                db.insert_row("products", {
                    "product_id": "PROD-003",
                    "product_name": "Biodegradable Packaging C",
                    "category": "packaging",
                    "sku": "BIO-PKG-C",
                    "unit_cost": 20.0,
                    "unit_price": 50.0,
                    "reorder_point": 15,
                    "reorder_quantity": 30,
                    "supplier_id": "SUP-002",
                    "is_active": 1,
                    "created_at": "2026-01-01T00:00:00Z"
                })
                logger.info("Products pre-populated from fallback mock list.")
                
        # Check if compliance events are empty
        comp_count = db.fetch_one("SELECT COUNT(*) as count FROM compliance_events")
        if comp_count and comp_count["count"] == 0:
            logger.info("Pre-populating compliance events...")
            csv_path = os.path.join(project_root, "database", "compliance_events.csv")
            csv_path_alt = os.path.join(project_root, "database", "calendar_events.csv")
            loaded_from_csv = False
            for path in (csv_path, csv_path_alt):
                if os.path.exists(path):
                    try:
                        with open(path, encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                db.insert_row("compliance_events", {
                                    "event_id": row.get("event_id"),
                                    "event_name": row.get("event_name"),
                                    "event_type": row.get("event_type"),
                                    "due_date": row.get("due_date"),
                                    "description": row.get("description"),
                                    "responsible_party": row.get("responsible_party"),
                                    "status": row.get("status"),
                                    "recurrence": row.get("recurrence"),
                                    "created_at": row.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                                })
                        loaded_from_csv = True
                        logger.info("Compliance events pre-populated from CSV.")
                        break
                    except Exception as ex:
                        logger.error(f"Failed to load compliance events from CSV: {ex}")
            
            if not loaded_from_csv:
                db.insert_row("compliance_events", {
                    "event_id": "EVT-DB-001",
                    "event_name": "Quarterly Corporate Tax Q2",
                    "event_type": "tax",
                    "due_date": "2026-06-30",
                    "description": "Quarterly corporate tax filing obligation.",
                    "responsible_party": "cfo",
                    "status": "pending",
                    "recurrence": "quarterly",
                    "created_at": "2026-06-01T00:00:00Z"
                })
                db.insert_row("compliance_events", {
                    "event_id": "EVT-DB-002",
                    "event_name": "Annual Health and Safety Inspector Audit",
                    "event_type": "regulatory",
                    "due_date": "2026-06-20", # Overdue relative to current date (2026-06-26)
                    "description": "Annual food production health and safety audit.",
                    "responsible_party": "ops_manager",
                    "status": "overdue",
                    "recurrence": "annual",
                    "created_at": "2026-06-01T00:00:00Z"
                })
                logger.info("Compliance events pre-populated from fallback mock list.")
    except Exception as e:
        logger.error(f"Failed to pre-populate database: {e}")
def pre_populate_history() -> None:
    """Pre-populate historical mock runs for BIZ-101 so the dashboard renders with data on first load."""
    import json
    import uuid
    from datetime import datetime, timezone, timedelta
    
    try:
        count = db.fetch_one("SELECT COUNT(*) as count FROM reports")
        if count and count["count"] > 0:
            return
            
        logger.info("Pre-populating historical runs for BIZ-101...")
        now = datetime.now(timezone.utc)
        
        # Seed 3 historical runs
        runs = [
            {
                "offset_days": 10,
                "health": 74,
                "business_risk": 48,
                "inventory": 52,
                "finance": 38,
                "supplier": 60,
                "compliance": 45,
                "priority_1": {
                    "action_title": "Address Supplier Delivery Performance",
                    "action_description": "Supplier SUP-001 delivery times have increased by 15%. Re-negotiate contract SLAs.",
                    "urgency": "this_week",
                    "expected_impact": "Medium"
                }
            },
            {
                "offset_days": 5,
                "health": 79,
                "business_risk": 42,
                "inventory": 40,
                "finance": 32,
                "supplier": 55,
                "compliance": 40,
                "priority_1": {
                    "action_title": "Resolve Overdue Regulatory Audit",
                    "action_description": "Ensure the annual health and safety audit is completed this week.",
                    "urgency": "immediate",
                    "expected_impact": "High"
                }
            },
            {
                "offset_days": 2,
                "health": 85,
                "business_risk": 35,
                "inventory": 30,
                "finance": 28,
                "supplier": 50,
                "compliance": 30,
                "priority_1": {
                    "action_title": "Reorder Eco Widget A Stock",
                    "action_description": "Stock of ECO-WID-A is down to 25 units. Place order with Alpha Supplies.",
                    "urgency": "this_week",
                    "expected_impact": "Medium"
                }
            }
        ]
        
        for run in runs:
            run_id = f"mock-run-{uuid.uuid4().hex[:8]}"
            recorded_at = (now - timedelta(days=run.get("offset_days", 0))).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # 1. Insert risk scores
            score_types = [
                ("inventory_agent", "inventory_risk", run["inventory"]),
                ("finance_agent", "finance_risk", run["finance"]),
                ("supplier_agent", "supplier_risk", run["supplier"]),
                ("compliance_agent", "compliance_risk", run["compliance"]),
                ("risk_tracker_agent", "business_risk", run["business_risk"]),
                ("strategy_agent", "business_health", run["health"])
            ]
            
            for agent, score_type, val in score_types:
                db.insert_row("risk_scores", {
                    "score_id": f"sc-{uuid.uuid4().hex[:8]}",
                    "agent_name": agent,
                    "score_type": score_type,
                    "score_value": val,
                    "run_id": run_id,
                    "recorded_at": recorded_at
                })
                
            # 2. Insert report
            content = {
                "business_id": "BIZ-101",
                "business_name": "Apex Enterprises Ltd",
                "business_type": "retail",
                "period_days": 30,
                "system_status": "success",
                "audit_trail": [
                    { "step": "adk_mcp_layer", "duration_ms": 1150, "timestamp": recorded_at, "status": "success" },
                    { "step": "adk_run_parallel_agents", "duration_ms": 2840, "timestamp": recorded_at, "status": "success" },
                    { "step": "adk_run_risk_tracker", "duration_ms": 820, "timestamp": recorded_at, "status": "success" },
                    { "step": "adk_run_strategy", "duration_ms": 940, "timestamp": recorded_at, "status": "success" },
                    { "step": "adk_run_communication", "duration_ms": 1420, "timestamp": recorded_at, "status": "success" },
                    { "step": "db_persistence_layer", "duration_ms": 180, "timestamp": recorded_at, "status": "success" }
                ],
                "mcp_data": {
                    "google_sheets_mcp_status": "success",
                    "calendar_mcp_status": "success",
                    "news_mcp_status": "success",
                    "supplier_intelligence_mcp_status": "success",
                    "risk_registry_mcp_status": "success"
                },
                "agent_reports": {
                    "business_risk_report": {
                        "business_risk_score": run["business_risk"],
                        "risk_breakdown": {
                            "inventory_risk_score": run["inventory"],
                            "finance_risk_score": run["finance"],
                            "supplier_risk_score": run["supplier"],
                            "compliance_risk_score": run["compliance"]
                        },
                        "critical_risks": [
                            {"domain": "supplier", "score": run["supplier"], "severity": "medium" if run["supplier"] < 70 else "high"}
                        ] if run["supplier"] >= 55 else []
                    },
                    "strategy_report": {
                        "business_health_score": run["health"],
                        "priority_1_action": run["priority_1"],
                        "priority_2_action": {
                            "action_title": "Optimize Working Capital",
                            "action_description": "Review current accounts receivables to improve overall cash flow balance.",
                            "urgency": "later",
                            "expected_impact": "Low"
                        }
                    },
                    "communication_draft": {
                        "ceo_briefing": "Historical demo run briefing context. Operations are stable.",
                        "email_draft": {
                            "subject": "Business Guardian AI - Daily Briefing Summary",
                            "body": "Hi Team, here is the automated risk assessment update."
                        }
                    }
                }
            }
            
            db.insert_row("reports", {
                "report_id": f"rep-{uuid.uuid4().hex[:8]}",
                "run_id": run_id,
                "business_id": "BIZ-101",
                "business_name": "Apex Enterprises Ltd",
                "report_type": "full_analysis",
                "content": json.dumps(content),
                "system_status": "success",
                "generated_at": recorded_at
            })
            
        logger.info("Historical mock runs successfully seeded.")
    except Exception as e:
        logger.error(f"Failed to seed history: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager for application startup and shutdown events."""
    logger.info("Starting Business Guardian AI backend...")
    db.initialize_db()
    pre_populate_database()
    pre_populate_history()
    yield
    logger.info("Shutting down Business Guardian AI backend...")

app = FastAPI(
    title="🛡️ Business Guardian AI - Core Engine API",
    description="""
    ## Proactive Operational Risk Intelligence Portal
    
    Welcome to the commercial-grade API documentation for the **Business Guardian AI** platform.
    This backend exposes the multi-agent orchestrator driven by **Google ADK** that ingests small business operational data, queries tools via **Model Context Protocol (MCP)**, and outputs explainable risk assessments.
    
    ### Key Features:
    * 🤖 **Multi-Agent Orchestration**: Coordinate parallel assessments from Inventory, Finance, Supplier, and Compliance agents.
    * ⚖️ **Human-in-the-Loop (HITL)**: Secure approval gates before finalizing communication drafts.
    * 🔄 **Resilient Fallbacks**: Auto-switch to deterministic rules when Gemini APIs hit rate limits.
    """,
    version="1.0.0",
    lifespan=lifespan
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Root landing page for backend API.")
async def root():
    from fastapi.responses import HTMLResponse
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Business Guardian AI Backend</title>
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
            <h1>Business Guardian AI Backend</h1>
            <p>This is the FastAPI backend service for the Business Guardian AI pipeline. It exposes REST API endpoints for agent analysis and database persistence.</p>
            <a class="btn" href="https://business-guardian-ai-frontend.onrender.com">Go to Business Dashboard</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi import Response
    return Response(status_code=204)

@app.post("/analyze", summary="Trigger a new operational risk analysis run.", dependencies=[Depends(verify_api_key)])
async def post_analyze(payload: AnalyzeRequest):
    """Intake an analysis request, execute MCP fetches and Agent Phase 1."""
    inputs = payload.model_dump()
    result = await orchestrator.start_analysis(inputs)
    return result

@app.post("/analyze/approve", summary="Approve or reject a paused draft communication plan.", dependencies=[Depends(verify_api_key)])
async def post_approve(payload: ApproveRequest):
    """Resume the analysis run to trigger validation checks and reports persistence."""
    run_id = payload.run_id
    status = payload.approval_status
    
    if status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="approval_status must be 'approved' or 'rejected'.")
        
    approved = (status == "approved")
    result = await orchestrator.approve_analysis(run_id, approved)
    return result

def normalize_business_id(biz_id: str) -> str:
    """Normalize business IDs (e.g., 'BIZ 101' -> 'BIZ-101', 'biz-101' -> 'BIZ-101')."""
    return biz_id.strip().replace(" ", "-").upper()

@app.get("/reports", summary="Retrieve historical generated reports for a business.", dependencies=[Depends(verify_api_key)])
def get_reports(business_id: str = Query(..., description="UUID of the corporate entity.")):
    """Fetch stored full analysis reports from SQLite database."""
    normalized_id = normalize_business_id(business_id)
    query = "SELECT * FROM reports WHERE business_id = ? ORDER BY generated_at DESC"
    reports_list = db.fetch_all(query, (normalized_id,))
    
    # Return formatted reports
    import json
    for r in reports_list:
        if isinstance(r.get("content"), str):
            try:
                r["content"] = json.loads(r["content"])
            except ValueError:
                pass
    return reports_list

@app.get("/history", summary="Query risk score trends for a business.", dependencies=[Depends(verify_api_key)])
def get_history(business_id: str = Query(..., description="UUID of the corporate entity.")):
    """Fetch stored risk scores from SQLite database, grouped by run_id for frontend compatibility."""
    normalized_id = normalize_business_id(business_id)
    query = """
        SELECT rs.run_id, rs.score_type, rs.score_value, rs.recorded_at 
        FROM risk_scores rs
        JOIN reports r ON rs.run_id = r.run_id
        WHERE r.business_id = ?
        ORDER BY rs.recorded_at DESC
    """
    raw_scores = db.fetch_all(query, (normalized_id,))
    
    # Group scores by run_id
    runs_dict = {}
    for row in raw_scores:
        rid = row["run_id"]
        if rid not in runs_dict:
            runs_dict[rid] = {
                "run_id": rid,
                "recorded_at": row["recorded_at"]
            }
        
        s_type = row["score_type"]
        val = row["score_value"]
        
        # Map DB score types to the exact keys expected by the frontend Dashboard component
        if s_type == "business_risk":
            runs_dict[rid]["overall_risk_score"] = val
        elif s_type == "business_health":
            runs_dict[rid]["business_health_score"] = val
        elif s_type == "inventory_risk":
            runs_dict[rid]["inventory_risk"] = val
        elif s_type == "finance_risk":
            runs_dict[rid]["finance_risk"] = val
        elif s_type == "supplier_risk":
            runs_dict[rid]["supplier_risk"] = val
        elif s_type == "compliance_risk":
            runs_dict[rid]["compliance_risk"] = val

    # Sort runs chronologically descending
    consolidated_runs = list(runs_dict.values())
    consolidated_runs.sort(key=lambda x: x["recorded_at"], reverse=True)
    return consolidated_runs

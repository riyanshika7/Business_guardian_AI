"""Workflow — coordinates MCP data gathering, parallel/sequential agent execution, and database persistence using Google ADK 2.0."""

from __future__ import annotations
import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic import BaseModel, Field
from google.adk import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.adk.agents.base_agent import BaseAgent
from typing import AsyncGenerator
from google.adk.events.event import Event
from google.genai.types import Content, Part
import json
from pathlib import Path

from database import db
from guardrails.audit_logger import log_event
from guardrails import hitl_guardrail
from mcp_servers import sheets_mcp, calendar_mcp, news_mcp, supplier_intelligence_mcp, risk_registry_mcp
from agents import (
    inventory_agent, finance_agent, supplier_agent, compliance_agent,
    risk_tracker_agent, strategy_agent, communication_agent, evaluation_agent
)

logger = logging.getLogger(__name__)


# ===================================================================
# ADK 2.0 State Definition
# ===================================================================

class WorkflowState(BaseModel):
    """ADK-compatible shared state schema for the Business Guardian AI pipeline.
    
    Contains all operational inputs, temporary variables, MCP records,
    agent outputs, confidence scores, and auditing metadata.
    """
    # User Request & Context
    run_id: str = ""
    business_id: str = ""
    business_name: str = ""
    business_type: str = "retail"
    recipient_name: str = "Business Owner"
    communication_type: str = "both"
    period_days: int = 30
    analysis_window_days: int = 30
    current_date: str = ""
    
    # Session identifiers
    adk_session_id: str = ""
    approval_status: str = ""
    
    # Pipeline status & errors
    system_status: str = "initialized"
    errors: list[dict[str, Any]] = Field(default_factory=list)
    products: list[dict[str, Any]] = Field(default_factory=list)
    
    # Ingested MCP data
    mcp_data: dict[str, Any] = Field(default_factory=dict)
    
    # Inter-agent outputs
    agent_reports: dict[str, Any] = Field(default_factory=dict)
    guardrail_state: dict[str, Any] = Field(default_factory=dict)
    
    # Evaluation outcomes
    confidence_score: int = 100
    validation_status: str = "passed"
    
    # Auditing / Observability metadata
    execution_metadata: dict[str, Any] = Field(default_factory=dict)
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


# ===================================================================
# ADK 2.0 Graph Node Implementations (Callable step functions)
# ===================================================================

async def adk_mcp_layer(ctx: Any) -> None:
    """ADK Node wrapping the concurrent external MCP ingestion layer."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_mcp_layer execution")
    
    run_id = ctx.state.get("run_id")
    business_id = ctx.state.get("business_id")
    business_type = ctx.state.get("business_type")
    period_days = ctx.state.get("period_days")
    analysis_window_days = ctx.state.get("analysis_window_days")
    
    # 0. Load products from SQLite database (Pipeline initialization)
    try:
        products_db = db.fetch_all("SELECT * FROM products WHERE is_active = 1")
        ctx.state.update({"products": products_db})
    except Exception as pe:
        logger.error(f"Failed to load products during pipeline initialization: {pe}")
        ctx.state.update({"products": []})

    # Batch 1: Ingest Sheets, Calendar, and Risk Registry in parallel
    async def call_sheets():
        log_event(run_id, "mcp_call_start", agent_name=None, input_payload={"spreadsheet_id": "config_env", "sheets": ["inventory", "sales", "expenses", "suppliers"]})
        t0_call = datetime.now(timezone.utc)
        sheets_inputs = {
            "spreadsheet_id": "spreadsheet-12345",
            "sheets": ["inventory", "sales", "expenses", "suppliers"],
            "date_range": {
                "start_date": (datetime.now(timezone.utc) - timedelta(days=period_days)).strftime("%Y-%m-%d"),
                "end_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
        }
        res = await asyncio.to_thread(sheets_mcp.fetch_sheets_data, sheets_inputs)
        dur = int((datetime.now(timezone.utc) - t0_call).total_seconds() * 1000)
        if res["status"] == "error":
            log_event(run_id, "mcp_call_error", error_code=res["error_code"], duration_ms=dur)
            return ("sheets", False, res)
        log_event(run_id, "mcp_call_complete", duration_ms=dur)
        return ("sheets", True, res)

    async def call_calendar():
        log_event(run_id, "mcp_call_start", input_payload={"calendar_id": "corporate_cal", "look_ahead_days": analysis_window_days})
        t0_call = datetime.now(timezone.utc)
        res = await asyncio.to_thread(calendar_mcp.fetch_calendar_data, {
            "calendar_id": "calendar-12345",
            "look_ahead_days": analysis_window_days
        })
        dur = int((datetime.now(timezone.utc) - t0_call).total_seconds() * 1000)
        if res["status"] == "error":
            log_event(run_id, "mcp_call_error", error_code=res["error_code"], duration_ms=dur)
            return ("calendar", False, res)
        log_event(run_id, "mcp_call_complete", duration_ms=dur)
        return ("calendar", True, res)

    async def call_risk_registry():
        log_event(run_id, "mcp_call_start", input_payload={"business_id": business_id})
        t0_call = datetime.now(timezone.utc)
        res = await asyncio.to_thread(risk_registry_mcp.fetch_risk_history, {
            "business_id": business_id,
            "history_days": 90
        })
        dur = int((datetime.now(timezone.utc) - t0_call).total_seconds() * 1000)
        if res["status"] == "error":
            log_event(run_id, "mcp_call_error", error_code=res["error_code"], duration_ms=dur)
            return ("risk_registry", False, res)
        log_event(run_id, "mcp_call_complete", duration_ms=dur)
        return ("risk_registry", True, res)

    batch1_results = await asyncio.gather(
        call_sheets(),
        call_calendar(),
        call_risk_registry()
    )

    mcp_data = ctx.state.get("mcp_data") or {}
    errors = ctx.state.get("errors") or []

    # Process Batch 1 results (Sheets and Calendar are critical, Risk Registry is degraded)
    for name, success, res in batch1_results:
        if name == "sheets":
            if not success:
                mcp_data["google_sheets_mcp_status"] = "error"
                mcp_data["calendar_mcp_status"] = "skipped"
                mcp_data["news_mcp_status"] = "skipped"
                mcp_data["supplier_intelligence_mcp_status"] = "skipped"
                mcp_data["risk_registry_mcp_status"] = "skipped"
                errors.append(res)
                ctx.state.update({
                    "mcp_data": mcp_data,
                    "errors": errors,
                    "system_status": "error"
                })
                raise RuntimeError(f"Sheets MCP failed: {res['error_message']}")
            mcp_data["google_sheets_mcp_status"] = "success"
            mcp_data["inventory_data"] = res["data"].get("inventory", [])
            mcp_data["sales_data"] = res["data"].get("sales", [])
            mcp_data["expenses_data"] = res["data"].get("expenses", [])
            mcp_data["supplier_data"] = res["data"].get("suppliers", [])
            
        elif name == "calendar":
            if not success:
                mcp_data["calendar_mcp_status"] = "error"
                errors.append(res)
                ctx.state.update({
                    "mcp_data": mcp_data,
                    "errors": errors,
                    "system_status": "error"
                })
                raise RuntimeError(f"Calendar MCP failed: {res['error_message']}")
            mcp_data["calendar_mcp_status"] = "success"
            mcp_data["compliance_data"] = res["data"].get("calendar_events", [])
            
        elif name == "risk_registry":
            if not success:
                mcp_data["risk_registry_mcp_status"] = "degraded"
                mcp_data["risk_history"] = []
                mcp_data["risk_status"] = {}
                mcp_data["risk_trends"] = []
                errors.append(res)
                ctx.state.update({
                    "mcp_data": mcp_data,
                    "errors": errors,
                    "system_status": "degraded"
                })
            else:
                mcp_data["risk_registry_mcp_status"] = "success"
                mcp_data["risk_history"] = res["data"].get("risk_history", [])
                mcp_data["risk_status"] = res["data"].get("risk_status", {})
                mcp_data["risk_trends"] = res["data"].get("risk_trends", [])

    # Extract suppliers list (from Batch 1 Sheets result)
    suppliers_list = mcp_data["supplier_data"]
    supplier_ids = [s["supplier_id"] for s in suppliers_list if "supplier_id" in s]
    supplier_names = [s["supplier_name"] for s in suppliers_list if "supplier_name" in s]

    # Setup industry keywords based on business type
    industry_keywords = ["supply chain"]
    if business_type == "retail":
        industry_keywords = ["retail", "consumer demand"]
    elif business_type == "agriculture":
        industry_keywords = ["agriculture", "crop yield", "weather risk"]
    elif business_type == "ecommerce":
        industry_keywords = ["ecommerce", "online retail", "shipping rates"]

    # Batch 2: Ingest News and Supplier Intelligence in parallel
    async def call_news():
        log_event(run_id, "mcp_call_start", input_payload={"supplier_names": supplier_names, "keywords": industry_keywords})
        t0_call = datetime.now(timezone.utc)
        res = await asyncio.to_thread(news_mcp.fetch_news_data, {
            "supplier_names": supplier_names,
            "industry_keywords": industry_keywords,
            "max_articles_per_topic": 5,
            "max_age_days": 30
        })
        dur = int((datetime.now(timezone.utc) - t0_call).total_seconds() * 1000)
        if res["status"] == "error":
            log_event(run_id, "mcp_call_error", error_code=res["error_code"], duration_ms=dur)
            return ("news", False, res)
        log_event(run_id, "mcp_call_complete", duration_ms=dur)
        return ("news", True, res)

    async def call_supplier_intel():
        log_event(run_id, "mcp_call_start", input_payload={"supplier_ids": supplier_ids})
        t0_call = datetime.now(timezone.utc)
        res = await asyncio.to_thread(supplier_intelligence_mcp.fetch_supplier_intelligence, {
            "supplier_ids": supplier_ids,
            "include_history": True,
            "history_months": 6
        })
        dur = int((datetime.now(timezone.utc) - t0_call).total_seconds() * 1000)
        if res["status"] == "error":
            log_event(run_id, "mcp_call_error", error_code=res["error_code"], duration_ms=dur)
            return ("supplier_intel", False, res)
        log_event(run_id, "mcp_call_complete", duration_ms=dur)
        return ("supplier_intel", True, res)

    batch2_results = await asyncio.gather(
        call_news(),
        call_supplier_intel()
    )

    # Process Batch 2 results (Supplier Intel is critical, News is degraded)
    for name, success, res in batch2_results:
        if name == "supplier_intel":
            if not success:
                mcp_data["supplier_intelligence_mcp_status"] = "error"
                errors.append(res)
                ctx.state.update({
                    "mcp_data": mcp_data,
                    "errors": errors,
                    "system_status": "error"
                })
                raise RuntimeError(f"Supplier Intelligence MCP failed: {res['error_message']}")
            mcp_data["supplier_intelligence_mcp_status"] = "success"
            mcp_data["supplier_intelligence"] = res["data"]
            
        elif name == "news":
            if not success:
                mcp_data["news_mcp_status"] = "degraded"
                mcp_data["supplier_news"] = []
                errors.append(res)
                ctx.state.update({
                    "mcp_data": mcp_data,
                    "errors": errors,
                    "system_status": "degraded"
                })
            else:
                mcp_data["news_mcp_status"] = "success"
                mcp_data["supplier_news"] = res["data"].get("supplier_news", [])

    # Recursively sanitize all loaded string payloads to protect against prompt injection
    def sanitize_mcp_data(data, key_name=None):
        from guardrails.validation_guardrail import sanitize_input_string
        if isinstance(data, str):
            return sanitize_input_string(data, run_id=run_id, field_name=key_name)
        elif isinstance(data, list):
            return [sanitize_mcp_data(item, key_name) for item in data]
        elif isinstance(data, dict):
            return {key: sanitize_mcp_data(val, key) for key, val in data.items()}
        return data

    mcp_data = sanitize_mcp_data(mcp_data)
    
    # Calculate execution metrics
    dur_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["mcp_ingestion_layer"] = {
        "duration_ms": dur_ms,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "mcp_ingestion_layer",
        "duration_ms": dur_ms,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    ctx.state.update({
        "mcp_data": mcp_data,
        "errors": errors,
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


async def adk_run_parallel_agents(ctx: Any) -> None:
    """ADK Node executing Core Domain Agents in parallel."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_run_parallel_agents execution")
    
    run_id = ctx.state.get("run_id")
    business_type = ctx.state.get("business_type")
    period_days = ctx.state.get("period_days")
    analysis_window_days = ctx.state.get("analysis_window_days")
    
    products_db = ctx.state.get("products", [])
    mcp_data = ctx.state.get("mcp_data", {})
    compliance_db = db.fetch_all("SELECT * FROM compliance_events")
    
    # Inputs mapping
    inv_inputs = {
        "products": products_db,
        "inventory": mcp_data.get("inventory_data", []),
        "sales": mcp_data.get("sales_data", []),
        "business_type": business_type
    }
    
    fin_inputs = {
        "sales": mcp_data.get("sales_data", []),
        "expenses": mcp_data.get("expenses_data", []),
        "period_days": period_days,
        "business_type": business_type
    }
    
    sup_inputs = {
        "suppliers": mcp_data.get("supplier_data", []),
        "supplier_intelligence": mcp_data.get("supplier_intelligence", {}),
        "supplier_news": mcp_data.get("supplier_news", []),
        "business_type": business_type
    }
    
    com_inputs = {
        "compliance_events": compliance_db,
        "calendar_events": mcp_data.get("compliance_data", []),
        "analysis_window_days": analysis_window_days,
        "business_type": business_type
    }
    
    async def run_agent(agent_module, name, inputs):
        log_event(run_id, "agent_dispatch", agent_name=name, input_payload={"keys": list(inputs.keys())})
        t0_run = datetime.now(timezone.utc)
        res = await asyncio.to_thread(agent_module.run, inputs)
        dur = int((datetime.now(timezone.utc) - t0_run).total_seconds() * 1000)
        
        if res.get("status") == "error":
            log_event(run_id, "agent_error", agent_name=name, error_code=res.get("error_code"), duration_ms=dur)
            return (name, False, res)
        log_event(run_id, "agent_complete", agent_name=name, duration_ms=dur)
        return (name, True, res)
        
    agent_runs = await asyncio.gather(
        run_agent(inventory_agent, "inventory_agent", inv_inputs),
        run_agent(finance_agent, "finance_agent", fin_inputs),
        run_agent(supplier_agent, "supplier_agent", sup_inputs),
        run_agent(compliance_agent, "compliance_agent", com_inputs)
    )
    
    agent_reports = ctx.state.get("agent_reports") or {}
    errors = ctx.state.get("errors") or []
    
    for name, success, res in agent_runs:
        if not success:
            errors.append(res)
            ctx.state.update({
                "errors": errors,
                "system_status": "error"
            })
            raise RuntimeError(f"Parallel Agent '{name}' failed: {res.get('error_message')}")
        agent_name = res["agent"]
        if agent_name.endswith("_agent"):
            report_key = agent_name.replace("_agent", "_risk_report")
            agent_reports[report_key] = res
        else:
            agent_reports[agent_name] = res
            
    dur_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["core_agents_layer"] = {
        "duration_ms": dur_ms,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "core_agents_layer",
        "duration_ms": dur_ms,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    ctx.state.update({
        "agent_reports": agent_reports,
        "errors": errors,
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


async def adk_run_risk_tracker(ctx: Any) -> None:
    """ADK Node executing the Risk Tracker Agent sequentially."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_run_risk_tracker execution")
    
    run_id = ctx.state.get("run_id")
    agent_reports = ctx.state.get("agent_reports", {})
    mcp_data = ctx.state.get("mcp_data", {})
    business_type = ctx.state.get("business_type")
    
    tracker_inputs = {
        "inventory_risk_report": agent_reports["inventory_risk_report"],
        "finance_risk_report": agent_reports["finance_risk_report"],
        "supplier_risk_report": agent_reports["supplier_risk_report"],
        "compliance_risk_report": agent_reports["compliance_risk_report"],
        "risk_history": mcp_data.get("risk_history", []),
        "business_type": business_type
    }
    
    log_event(run_id, "agent_dispatch", agent_name="risk_tracker_agent")
    res = await asyncio.to_thread(risk_tracker_agent.run, tracker_inputs)
    dur = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    
    if res.get("status") == "error":
        log_event(run_id, "agent_error", agent_name="risk_tracker_agent", error_code=res.get("error_code"), duration_ms=dur)
        ctx.state.update({"system_status": "error"})
        raise RuntimeError(f"Risk Tracker Agent failed: {res.get('error_message')}")
        
    log_event(run_id, "agent_complete", agent_name="risk_tracker_agent", duration_ms=dur)
    agent_reports["business_risk_report"] = res
    
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["risk_tracker_agent"] = {
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "risk_tracker_agent",
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    ctx.state.update({
        "agent_reports": agent_reports,
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


async def adk_run_strategy(ctx: Any) -> None:
    """ADK Node executing the Strategy Agent sequentially."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_run_strategy execution")
    
    run_id = ctx.state.get("run_id")
    agent_reports = ctx.state.get("agent_reports", {})
    business_type = ctx.state.get("business_type")
    
    strategy_inputs = {
        "business_risk_report": agent_reports["business_risk_report"],
        "inventory_risk_report": agent_reports["inventory_risk_report"],
        "finance_risk_report": agent_reports["finance_risk_report"],
        "supplier_risk_report": agent_reports["supplier_risk_report"],
        "compliance_risk_report": agent_reports["compliance_risk_report"],
        "business_type": business_type
    }
    
    log_event(run_id, "agent_dispatch", agent_name="strategy_agent")
    res = await asyncio.to_thread(strategy_agent.run, strategy_inputs)
    dur = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    
    if res.get("status") == "error":
        log_event(run_id, "agent_error", agent_name="strategy_agent", error_code=res.get("error_code"), duration_ms=dur)
        ctx.state.update({"system_status": "error"})
        raise RuntimeError(f"Strategy Agent failed: {res.get('error_message')}")
        
    log_event(run_id, "agent_complete", agent_name="strategy_agent", duration_ms=dur)
    agent_reports["strategy_report"] = res
    
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["strategy_agent"] = {
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "strategy_agent",
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    ctx.state.update({
        "agent_reports": agent_reports,
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


async def adk_run_communication(ctx: Any) -> None:
    """ADK Node executing the Communication Agent and pausing at the HITL approval gate."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_run_communication execution")
    
    run_id = ctx.state.get("run_id")
    agent_reports = ctx.state.get("agent_reports", {})
    business_name = ctx.state.get("business_name")
    recipient_name = ctx.state.get("recipient_name")
    comm_type = ctx.state.get("communication_type")
    
    comm_inputs = {
        "strategy_report": agent_reports["strategy_report"],
        "business_risk_report": agent_reports["business_risk_report"],
        "inventory_risk_report": agent_reports["inventory_risk_report"],
        "finance_risk_report": agent_reports["finance_risk_report"],
        "supplier_risk_report": agent_reports["supplier_risk_report"],
        "compliance_risk_report": agent_reports["compliance_risk_report"],
        "business_name": business_name,
        "recipient_name": recipient_name,
        "communication_type": comm_type
    }
    
    log_event(run_id, "agent_dispatch", agent_name="communication_agent")
    res = await asyncio.to_thread(communication_agent.run, comm_inputs)
    dur = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    
    if res.get("status") == "error":
        log_event(run_id, "agent_error", agent_name="communication_agent", error_code=res.get("error_code"), duration_ms=dur)
        ctx.state.update({"system_status": "error"})
        raise RuntimeError(f"Communication Agent failed: {res.get('error_message')}")
        
    log_event(run_id, "agent_complete", agent_name="communication_agent", duration_ms=dur)
    agent_reports["communication_draft"] = res
    
    # Save HITL pending approval checkpoint state
    hitl_pending = hitl_guardrail.create_hitl_pending_state(res, run_id)
    guardrail_state = ctx.state.get("guardrail_state") or {}
    guardrail_state["human_approval_status"] = "pending"
    guardrail_state["approval_id"] = hitl_pending["approval_id"]
    
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["communication_agent"] = {
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "communication_agent",
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    log_event(run_id, "guardrail_hitl_pending", agent_name="communication_agent", output_payload=hitl_pending)
    
    ctx.state.update({
        "agent_reports": agent_reports,
        "guardrail_state": guardrail_state,
        "system_status": "awaiting_human_approval",
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


async def adk_run_evaluation(ctx: Any) -> None:
    """ADK Node resolving HITL outcomes and invoking the Evaluation Agent (Phase 2)."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_run_evaluation execution")
    
    run_id = ctx.state.get("run_id")
    guardrail_state = ctx.state.get("guardrail_state", {})
    agent_reports = ctx.state.get("agent_reports", {})
    
    approved = (ctx.state.get("approval_status") == "approved")
    approval_id = guardrail_state.get("approval_id")
    
    if not approved:
        # Rejected pathway
        hitl_guardrail.reject(approval_id)
        guardrail_state["human_approval_status"] = "rejected"
        
        err_res = {
            "agent": "orchestrator",
            "status": "error",
            "error_code": "HITL_REJECTED",
            "error_message": "The generated communication draft was rejected by a human operator."
        }
        errors = ctx.state.get("errors") or []
        errors.append(err_res)
        log_event(run_id, "guardrail_hitl_rejected")
        
        ctx.state.update({
            "guardrail_state": guardrail_state,
            "errors": errors,
            "system_status": "error"
        })
        return
        
    # Approved pathway
    hitl_guardrail.approve(approval_id)
    guardrail_state["human_approval_status"] = "approved"
    log_event(run_id, "guardrail_hitl_approved")
    
    # Dispatch Evaluation Agent
    eval_inputs = {
        "inventory_risk_report": agent_reports["inventory_risk_report"],
        "finance_risk_report": agent_reports["finance_risk_report"],
        "supplier_risk_report": agent_reports["supplier_risk_report"],
        "compliance_risk_report": agent_reports["compliance_risk_report"],
        "business_risk_report": agent_reports["business_risk_report"],
        "strategy_report": agent_reports["strategy_report"],
        "communication_draft": agent_reports["communication_draft"]
    }
    
    log_event(run_id, "agent_dispatch", agent_name="evaluation_agent")
    res = await asyncio.to_thread(evaluation_agent.run, eval_inputs)
    dur = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    
    if res.get("status") == "error":
        log_event(run_id, "agent_error", agent_name="evaluation_agent", error_code=res.get("error_code"), duration_ms=dur)
        ctx.state.update({"system_status": "error"})
        raise RuntimeError(f"Evaluation Agent failed: {res.get('error_message')}")
        
    log_event(run_id, "agent_complete", agent_name="evaluation_agent", duration_ms=dur)
    agent_reports["evaluation_report"] = res
    
    # Extract evaluation details
    guardrail_state["validation_details"] = res.get("validation_details", [])
    guardrail_state["warnings"] = res.get("warnings", [])
    
    # Confidence threshold checks
    system_status = ctx.state.get("system_status")
    if res.get("human_review_flag", False):
        system_status = "human_review_required"
        log_event(run_id, "guardrail_confidence_flagged")
    else:
        if system_status != "degraded":
            system_status = "success"
            
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["evaluation_agent"] = {
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "evaluation_agent",
        "duration_ms": dur,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    ctx.state.update({
        "guardrail_state": guardrail_state,
        "agent_reports": agent_reports,
        "system_status": system_status,
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


async def adk_persist_report(ctx: Any) -> None:
    """ADK Node persisting E2E report schemas to DB."""
    t0 = datetime.now(timezone.utc)
    logger.info("[ADK NODE] Starting adk_persist_report execution")
    
    run_id = ctx.state.get("run_id")
    business_id = ctx.state.get("business_id")
    business_name = ctx.state.get("business_name")
    system_status = ctx.state.get("system_status")
    agent_reports = ctx.state.get("agent_reports", {})
    
    if system_status == "error":
        return
        
    try:
        run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Save inventory risk score
        db.insert_row("risk_scores", {
            "agent_name": "inventory_agent",
            "score_type": "inventory_risk",
            "score_value": agent_reports["inventory_risk_report"].get("inventory_risk_score", 0),
            "run_id": run_id,
            "recorded_at": run_timestamp
        })
        
        # Save finance risk score
        db.insert_row("risk_scores", {
            "agent_name": "finance_agent",
            "score_type": "finance_risk",
            "score_value": agent_reports["finance_risk_report"].get("finance_risk_score", 0),
            "run_id": run_id,
            "recorded_at": run_timestamp
        })
        
        # Save supplier risk score
        db.insert_row("risk_scores", {
            "agent_name": "supplier_agent",
            "score_type": "supplier_risk",
            "score_value": agent_reports["supplier_risk_report"].get("supplier_risk_score", 0),
            "run_id": run_id,
            "recorded_at": run_timestamp
        })
        
        # Save compliance risk score
        db.insert_row("risk_scores", {
            "agent_name": "compliance_agent",
            "score_type": "compliance_risk",
            "score_value": agent_reports["compliance_risk_report"].get("compliance_risk_score", 0),
            "run_id": run_id,
            "recorded_at": run_timestamp
        })
        
        # Save aggregate business risk score
        db.insert_row("risk_scores", {
            "agent_name": "risk_tracker_agent",
            "score_type": "business_risk",
            "score_value": agent_reports["business_risk_report"].get("business_risk_score", 0),
            "run_id": run_id,
            "recorded_at": run_timestamp
        })
        
        # Save full analysis report to database
        state_dict = ctx.state.to_dict() if hasattr(ctx.state, "to_dict") else ctx.state
        db.insert_row("reports", {
            "report_id": str(uuid.uuid4()),
            "run_id": run_id,
            "business_id": business_id,
            "business_name": business_name,
            "report_type": "full_analysis",
            "content": state_dict,
            "system_status": system_status,
            "generated_at": run_timestamp
        })
        
        logger.info(f"Successfully stored risk scores and report for run_id: {run_id} to DB.")
        
    except Exception as dbe:
        logger.error(f"Failed to persist risk scores or report to DB: {dbe}")
        
    dur_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    exec_metadata = ctx.state.get("execution_metadata") or {}
    exec_metadata["db_persistence_layer"] = {
        "duration_ms": dur_ms,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    }
    
    audit_trail = ctx.state.get("audit_trail") or []
    audit_trail.append({
        "step": "db_persistence_layer",
        "duration_ms": dur_ms,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success"
    })
    
    ctx.state.update({
        "execution_metadata": exec_metadata,
        "audit_trail": audit_trail
    })


class Workflow(BaseAgent):
    """ADK-compatible Workflow class that implements linear pipeline node execution."""
    edges: list[tuple[Any, Any]] = Field(default_factory=list)
    state_schema: Any = None

    async def _run_async_impl(self, ctx: Any) -> AsyncGenerator[Event, None]:
        if not hasattr(ctx, "state"):
            ctx.state = ctx.session.state
        
        current_node = "START"
        visited = set()
        
        while True:
            next_edge = None
            for src, dest in self.edges:
                if src == current_node:
                    next_edge = (src, dest)
                    break
            
            if not next_edge:
                break
                
            src, dest = next_edge
            if dest in visited:
                break
            
            visited.add(dest)
            
            if callable(dest):
                logger.info(f"[Workflow {self.name}] Running node: {dest.__name__}")
                await dest(ctx)
                current_node = dest
            else:
                current_node = dest
                
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=None
        )


mcp_workflow = Workflow(
    name="mcp_workflow",
    state_schema=WorkflowState,
    edges=[
        ("START", adk_mcp_layer)
    ]
)

phase_1_workflow = Workflow(
    name="phase_1_workflow",
    state_schema=WorkflowState,
    edges=[
        ("START", adk_run_parallel_agents),
        (adk_run_parallel_agents, adk_run_risk_tracker),
        (adk_run_risk_tracker, adk_run_strategy),
        (adk_run_strategy, adk_run_communication)
    ]
)

phase_2_workflow = Workflow(
    name="phase_2_workflow",
    state_schema=WorkflowState,
    edges=[
        ("START", adk_run_evaluation),
        (adk_run_evaluation, adk_persist_report)
    ]
)


# ===================================================================
# ADK Execution Engine Helper
# ===================================================================

class PersistentSessionService(InMemorySessionService):
    """Custom ADK SessionService that serializes session states to local JSON files.

    This ensures that session contexts survive server restarts or application crashes.
    The cache directory defaults to a writable project-local path so it works across
    different Windows user accounts and environments.
    """
    def __init__(self, cache_dir: str | None = None):
        super().__init__()
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            project_root = Path(__file__).resolve().parent.parent
            self.cache_dir = project_root / ".cache" / "adk_sessions"
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(f"Falling back to temp directory for ADK session cache: {exc}")
            self.cache_dir = Path(tempfile.gettempdir()) / "business_guardian_adk_sessions"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        session = await super().create_session(
            app_name=app_name,
            user_id=user_id,
            state=state,
            session_id=session_id
        )
        
        cache_file = self.cache_dir / f"{session.id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    saved_state = json.load(f)
                session.state.update(saved_state)
                logger.info(f"Successfully restored persisted session {session.id} from local cache.")
            except Exception as e:
                logger.error(f"Failed to restore persisted session {session.id}: {e}")
                
        return session
        
    async def append_event(self, session: Session, event: Event) -> Event:
        event = await super().append_event(session, event)
        cache_file = self.cache_dir / f"{session.id}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(session.state, f)
        except Exception as e:
            logger.error(f"Failed to cache session state {session.id} to disk: {e}")
            
        return event

async def _run_adk_workflow(workflow_obj: Workflow, initial_state: dict[str, Any]) -> dict[str, Any]:
    """Helper utility to run an ADK Workflow through the Runner engine."""
    session_service = PersistentSessionService()
    runner = Runner(
        app_name="business_guardian_ai",
        agent=workflow_obj,
        session_service=session_service
    )
    user_id = initial_state.get("business_id", "default_user")
    session = await session_service.create_session(app_name="business_guardian_ai", user_id=user_id)
    session.state.update(initial_state)
    
    new_msg = Content(role="user", parts=[Part.from_text(text="Trigger workflow node")])
    async for event in runner.run_async(
        session_id=session.id,
        user_id=user_id,
        new_message=new_msg,
    ):
        if event.error_code:
            logger.error(f"[ADK ERROR EVENT] {event.error_code}: {event.error_message}")
            
    session_data = await session_service.get_session(session_id=session.id, app_name="business_guardian_ai", user_id=user_id)
    return session_data.state


# ===================================================================
# Public Orchestrator Pipeline APIs
# ===================================================================

async def execute_mcp_layer(state: dict[str, Any]) -> None:
    """Fetch external data from all 5 MCP sources using the ADK MCP workflow."""
    final_state = await _run_adk_workflow(mcp_workflow, state)
    state.clear()
    state.update(final_state)


async def execute_pipeline_phase_1(state: dict[str, Any]) -> None:
    """Execute parallel core agents, Risk Tracker, Strategy, and Communication Agent via ADK workflow."""
    final_state = await _run_adk_workflow(phase_1_workflow, state)
    state.clear()
    state.update(final_state)


async def execute_pipeline_phase_2(state: dict[str, Any], approved: bool) -> None:
    """Resume workflow from paused HITL gate using the ADK Evaluation workflow."""
    state["approval_status"] = "approved" if approved else "rejected"
    final_state = await _run_adk_workflow(phase_2_workflow, state)
    state.clear()
    state.update(final_state)

# Business Guardian AI — Threat Model & Security Diagnosis

**Date:** June 27, 2026  
**Target:** Business Guardian AI (Multi-Agent Operational Risk System)  
**Methodology:** STRIDE, Google Secure Agentic Coding, Business Impact Analysis, Multi-Agent Failure Matrix  

---

## Executive Summary

Business Guardian AI demonstrates an exceptionally mature internal security architecture for a hackathon project. The recent implementation of the `guardrails` package (HITL, validation, confidence, audit) strictly enforces Google Secure Agentic Coding principles, creating a robust, fault-isolated pipeline. The system effectively mitigates prompt injection, hallucination, and autonomous execution risks by centralizing tool access and mandating human approval. 

However, external security (authentication, API authorization) and state concurrency remain areas of weakness. The pipeline architecture also features a critical single point of failure at the Risk Tracker Agent.

## System Architecture & Trust Boundaries

The system follows a strict sequential-parallel pipeline:
`FastAPI Intake` → `MCP Layer (Fetch)` → `Domain Agents (Parallel)` → `Risk Tracker` → `Strategy` → `Communication` → `HITL Pause` → `Evaluation` → `SQLite`.

### Trust Boundaries
1. **Public vs. API Boundary**: User requests hitting `main.py` (`/analyze`, `/analyze/approve`). *Currently unauthenticated.*
2. **Execution Boundary**: `orchestrator.py` delegating to `workflow.py`.
3. **External Data Boundary**: `mcp/` layer fetching from untrusted external APIs (News, Sheets, Calendar).
4. **Security Boundary**: The `guardrails/` package validating all inputs/outputs before they cross agent boundaries.
5. **Persistence Boundary**: SQLite `business_guardian.db`. Read by Streamlit, written by FastAPI.

---

## STRIDE Findings

### 1. Spoofing
* **Finding**: The `/analyze/approve` endpoint accepts any `run_id` and does not validate the identity of the approver. The `hitl_guardrail.py` defaults to `approver="dashboard_user"`.
* **Risk**: Unauthorized users can approve critical business communications.

### 2. Tampering
* **Finding**: `SharedState` is passed as a mutable Python dictionary through `workflow.py`. While agents are given isolated slices, any bug in the workflow orchestrator could accidentally mutate upstream state. 
* **Risk**: Minimal internal risk due to strict validation, but SQLite database is unencrypted at rest and vulnerable to local file tampering.

### 3. Repudiation
* **Finding**: `audit_logger.py` performs excellent dual-sink logging (File + SQLite). 
* **Risk**: Due to the lack of identity management (Spoofing finding), malicious actions cannot be cryptographically tied to a specific human, breaking true non-repudiation.

### 4. Information Disclosure
* **Finding**: The `.env` file and `business_guardian.db` are stored in the project root. 
* **Risk**: If the FastAPI server misconfigures static file serving, the entire corporate intelligence database could be leaked via path traversal.

### 5. Denial of Service
* **Finding**: FastAPI lacks rate limiting. `workflow.py` dispatches parallel agents using `asyncio.to_thread`.
* **Risk**: A flood of `/analyze` requests will exhaust the asyncio thread pool and trigger massive rate-limit bans from the Gemini API, halting the platform.

### 6. Elevation of Privilege
* **Finding**: Excellent mitigation. Agents cannot call MCPs; they are "pure functions" fed by the orchestrator.
* **Risk**: Eliminated by design. No agent can elevate its privilege to execute unauthorized tools.

---

## Agentic Security Findings

Evaluated against **Google Secure Agentic Coding Principles**:

* ✅ **Input Validation**: `validation_guardrail.py` strictly validates `/analyze` payloads.
* ✅ **Output Validation**: 8 per-agent rule sets rigorously type-check all outputs, bounding scores to `[0, 100]`.
* ✅ **HITL Enforcement**: `hitl_guardrail.py` prevents external communication without human review.
* ✅ **Confidence Escalation**: `confidence_guardrail.py` deducts points for warnings/errors. Scores `< 60` trigger a mandatory review flag.
* ✅ **Audit Logging**: `audit_logger.py` tracks all MCP, agent, and pipeline events without crashing the main thread.
* ✅ **Failure Isolation**: Deep `try/except` blocks in the orchestrator ensure agent crashes return structured JSON rather than killing the server.
* ✅ **Tool Access Governance**: Agents have zero direct tool access (Data-in, Data-out paradigm).
* ✅ **Safe Error Handling**: Internal stack traces are logged but not returned to the client.

---

## Integration & Deployment Risks

* **Integration Risk (Concurrency)**: Streamlit (`reports.py`) and FastAPI (`main.py`) read/write to the same SQLite file. Under high load, SQLite will throw `database is locked` exceptions, crashing report generation.
* **Integration Risk (Timeouts)**: `config.py` defines `AGENT_TIMEOUT_SECONDS = 30`, but `asyncio.to_thread` does not natively enforce timeouts without `asyncio.wait_for()`.
* **Deployment Risk (Ephemeral Storage)**: Containerizing the app without mounting a volume will result in the loss of `business_guardian.db` and `logs/audit.log` on restart.

---

## Business Impact Analysis

| Component Failure | Business Impact | User Impact | Demo Impact | Severity |
|---|---|---|---|---|
| **Inventory Agent** | Cannot forecast stockouts. | UI shows missing inventory risk. | Partial degradation. | Medium |
| **Risk Tracker Agent** | Fails to aggregate domain scores. | Dashboard shows empty overall health. | Pipeline halts entirely. | **Critical** |
| **Communication Agent** | Hallucinates incorrect recommendations. | User receives bad advice. | Guardrail catches it (HITL). | High |
| **Supplier MCP** | Returns malformed risk data. | Supplier Agent falls back to defaults. | Domain degradation. | Medium |

---

## Multi-Agent Failure Analysis (Agent Failure Matrix)

| Agent | SPOF Risk | Upstream Dependency | Downstream Impact if Failed |
|---|---|---|---|
| **Domain Agents** (Inv, Fin, Sup, Comp) | Low | MCP Layer | Risk Tracker proceeds with missing domain data, penalizing confidence score. |
| **Risk Tracker** | **HIGH** | Domain Agents | Strategy Agent crashes (requires aggregated scores). |
| **Strategy** | **HIGH** | Risk Tracker | Communication Agent crashes (requires priority actions). |
| **Communication** | **HIGH** | Strategy Agent | HITL gate never triggers; pipeline halts. |
| **Evaluation** | **HIGH** | HITL Gate | Final database persistence fails; run is lost. |

> [!WARNING]  
> **Choke Point:** The Risk Tracker, Strategy, and Communication agents operate sequentially. A failure in any of these creates a Single Point of Failure (SPOF) that collapses the entire downstream pipeline.

---

## Hackathon Judge Perspective

* **Judge Score:** 9.0 / 10
* **Strengths:** 
  * World-class agentic security implementation. 
  * The separation of concerns (MCPs fetch, Agents think, Guardrails enforce, Orchestrator routes) is architectural perfection for LLM apps.
* **Weaknesses:** 
  * Lack of basic API authentication.
  * SQLite concurrency locking.
* **Most Impressive Component:** The `validation_guardrail.py` and `confidence_guardrail.py`. Translating raw LLM unpredictability into bounded `[0, 100]` integer risk scores with strict fallback penalties is brilliant.
* **Highest Risk Area:** The sequential SPOF chain (Risk Tracker → Strategy → Communication).

---

## Findings & Remediation

### [Critical Findings]
1. **Unauthenticated Endpoints:** Anyone can trigger expensive LLM pipelines via `/analyze`.
   * *Remediation:* Add basic API key validation to `main.py` using FastAPI's `Security` dependencies.

### [High Findings]
1. **Pipeline SPOF:** Risk Tracker agent failure halts the pipeline.
   * *Remediation:* Implement a fallback mechanism in `workflow.py` that generates a default "Empty" Risk Tracker report if the agent fails, allowing the pipeline to proceed with a severely penalized confidence score rather than crashing.
2. **SQLite Locking:** Concurrent read/writes will lock the DB.
   * *Remediation:* Add `timeout=10` to SQLite connection strings and enable WAL mode (`PRAGMA journal_mode=WAL;`).

### [Medium Findings]
1. **Missing Async Timeouts:** `AGENT_TIMEOUT_SECONDS` is defined but not enforced on agent threads.
   * *Remediation:* Wrap agent calls in `asyncio.wait_for(..., timeout=AGENT_TIMEOUT_SECONDS)`.
2. **Repudiation of Approval:** Approver identity is not verified.
   * *Remediation:* Pass actual user context from Streamlit/FastAPI into `approve_analysis()`.

### [Low Findings]
1. **Hardcoded DB Path:** DB is in the project root.
   * *Remediation:* Move to a dedicated `/data` folder to simplify Docker volume mapping.

---

## Final Scores

| Metric | Score | Note |
|---|---|---|
| **Security Score** | **85 / 100** | Exceptional internal guardrails; docked for lack of auth. |
| **Integration Readiness** | **90 / 100** | Highly cohesive architecture; docked for SPOF chain. |
| **Deployment Readiness** | **75 / 100** | Needs WAL mode for SQLite and environment variable hardening. |

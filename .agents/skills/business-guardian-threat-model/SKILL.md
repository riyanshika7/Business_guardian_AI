---
name: business-guardian-threat-model
description: Performs a comprehensive security and architecture review of the Business Guardian AI multi-agent system using STRIDE, agentic security principles, MCP security analysis, and Google Secure Agentic Coding practices. Use after major implementation milestones and before integration testing.
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Business Guardian AI Threat Modeling Skill

## Goal

Analyze the entire Business Guardian AI codebase, architecture documents, agents, MCPs, orchestrator, guardrails, database layer, API layer, and UI.

Generate a detailed:

threat_model.md

saved in the project root.

The report must identify security weaknesses, architecture risks, integration risks, deployment risks, and demo risks.

---

## Analysis Scope

Review:

* Project Constitution
* Team Context
* Agent Contracts
* API Contracts
* Data Models
* Orchestrator Contract

Review code:

* All Agents
* All MCPs
* Orchestrator
* Workflow
* Shared State
* Guardrails
* Database Layer
* FastAPI Backend
* Streamlit Dashboard
* Config Layer

---

## Phase 1 — System Boundary Analysis

Map:

User
↓
FastAPI
↓
Orchestrator
↓
Guardrails
↓
MCP Layer
↓
Agents
↓
Risk Tracker
↓
Strategy
↓
Communication
↓
Human Approval
↓
Evaluation
↓
Database
↓
Dashboard

Identify:

* Trust boundaries
* External systems
* Internal systems
* Sensitive data paths
* Approval boundaries

---

## Phase 2 — STRIDE Analysis

### Spoofing

Check:

* Human approval identity validation
* API caller validation
* MCP caller validation
* Agent impersonation risks

Questions:

Can unauthorized users approve reports?

Can one agent impersonate another?

Can MCP responses be spoofed?

---

### Tampering

Check:

* Shared state manipulation
* MCP response modification
* Database record modification
* Configuration tampering
* Prompt manipulation

Questions:

Can risk scores be altered?

Can agent outputs be modified before evaluation?

Can configuration values bypass guardrails?

---

### Repudiation

Check:

* Audit logging completeness
* Approval traceability
* Agent execution traceability
* MCP access logging

Questions:

Can a user deny approving a report?

Can an agent action occur without logging?

---

### Information Disclosure

Check:

* API responses
* Database records
* Logs
* Environment variables
* Gemini API keys
* Internal stack traces

Questions:

Can sensitive information leak?

Can internal architecture be exposed?

Can logs reveal secrets?

---

### Denial of Service

Check:

* MCP calls
* Gemini usage
* Database queries
* Agent loops
* Parallel execution

Questions:

Can a single request exhaust resources?

Can expensive operations be repeatedly triggered?

Can one failed MCP block the entire pipeline?

---

### Elevation of Privilege

Check:

* Tool access restrictions
* MCP permissions
* Agent permissions
* Approval workflows

Questions:

Can an agent access unauthorized MCPs?

Can a user bypass approval?

Can Evaluation Agent access privileged functions?

---

## Phase 3 — Agentic Security Review

Evaluate compliance with:

Google Secure Agentic Coding Principles

Check:

* Input validation
* Output validation
* HITL enforcement
* Confidence escalation
* Audit logging
* Failure isolation
* Safe error handling
* Tool access governance

---

## Phase 4 — Integration Risk Review

Simulate:

MCP Layer
↓
Core Agents
↓
Risk Tracker
↓
Strategy
↓
Communication
↓
HITL
↓
Evaluation

Identify:

* Missing dependencies
* Missing skills
* Missing guardrails
* Runtime failures
* Circular imports
* State inconsistencies

---

## Phase 5 — Deployment Readiness Review

Evaluate:

* Environment variables
* Config management
* Logging
* SQLite usage
* FastAPI security
* Streamlit security
* Production readiness

---

## Phase 6 — Business Impact Analysis

Evaluate:

- What happens if Inventory Agent fails?
- What happens if Risk Tracker produces incorrect scores?
- What happens if Communication Agent sends incorrect recommendations?
- What happens if Supplier Intelligence MCP returns corrupted data?

Classify impact as:
Critical
High
Medium
Low

Estimate:
- Business impact
- User impact
- Demo impact

---

## Phase 7 — Multi-Agent Failure Analysis

Analyze:

Inventory Agent
Finance Agent
Supplier Agent
Compliance Agent
Risk Tracker
Strategy Agent
Communication Agent
Evaluation Agent

For each agent identify:

- Single point of failure risks
- Missing fallback paths
- Invalid upstream dependencies
- Downstream impact if agent fails

Generate:
Agent Failure Matrix

---

## Phase 8 — Hackathon Judge Perspective

Evaluate project against:

- Architecture quality
- MCP usage
- Agent collaboration
- Security implementation
- Guardrails
- Human-in-the-loop
- Deployability
- Demonstration quality

Provide:

Judge Score (0-10)

Strengths
Weaknesses
Most impressive component
Highest risk area

---

## Output Requirements

Generate:

threat_model.md

with:

# Executive Summary

# System Architecture

# Trust Boundaries

# STRIDE Findings

# Agentic Security Findings

# Integration Risks

# Deployment Risks

# Critical Findings

# High Findings

# Medium Findings

# Low Findings

# Security Score (0-100)

# Integration Readiness Score (0-100)

# Deployment Readiness Score (0-100)

# Recommended Remediation Actions

Prioritize findings by severity and include exact file references whenever possible.

Do not generate code.

Act as a Senior Security Architect performing a pre-integration security assessment for a multi-agent AI platform.

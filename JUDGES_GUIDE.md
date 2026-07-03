# 🛡️ Business Guardian AI — Evaluator & Judge's Guide

Welcome! This guide outlines how to easily run, test, and evaluate the **Business Guardian AI** platform. The system is fully self-contained, pre-configured, and includes offline fallbacks to ensure a smooth evaluation experience on any machine.

---

## ⚡ Quick Start: One-Click Launch in VS Code

We have packaged a **VS Code Build Task** to start both the backend FastAPI service and the frontend React application simultaneously in two split terminals.

1. Open the project folder in **VS Code**.
2. Press **`Ctrl + Shift + B`** (or go to the top menu: **Terminal** ➜ **Run Build Task...**).
3. The terminal split panel will open and spin up:
   * **FastAPI Backend**: Running on [http://localhost:8000/](http://localhost:8000/)
   * **Vite React Frontend**: Running on [http://localhost:5173/](http://localhost:5173/)
4. Open your browser and navigate to the frontend URL: **[http://localhost:5173/](http://localhost:5173/)**

*(To stop the servers at any time, click in either terminal panel and press `Ctrl + C`).*

---

## 🎨 Key Features & Evaluation Walkthrough

### 1️⃣ Interactive Risk Intelligence Dashboard (Pre-Seeded Demo State)
* **What to look for**: When you first open the dashboard, it is **pre-populated with 10 days of historical trend graphs, past briefings, and action items** (for Corporate ID `BIZ-101`). 
* **Input Resiliency**: You can type the Business ID as either `BIZ 101` (with a space) or `BIZ-101` (with a hyphen)—the backend automatically normalizes the input to retrieve your data.

### 2️⃣ Triggering a Live Multi-Agent AI Analysis
* **How to run**: On the left-hand sidebar, customize the settings (Business Type, analysis period, etc.) and click **"Run Analysis"**.
* **What happens**: The **Google ADK Orchestration** launches multiple specialized agents in parallel:
  1. **Inventory Agent**: Checks stock records.
  2. **Finance Agent**: Analyzes revenue/expenses.
  3. **Supplier Agent**: Assesses supplier reliability.
  4. **Compliance Agent**: Checks regulatory deadlines.
  5. **Risk Tracker**: Combines everything into a unified operational risk profile.
* **Resiliency Check**: If the system detects API rate limits (Gemini 429 errors), it catches the exception and falls back to a **deterministic rule-based evaluation engine** to complete the analysis successfully instead of crashing.

### 3️⃣ Human-in-the-Loop (HITL) Gate
* **What to look for**: Once the live analysis completes, the pipeline pauses. A **"Human Review Required"** alert banner will appear inline on the dashboard.
* **Action**: Review the generated CEO brief and email draft, then click **"Approve Release"** or **"Reject & Purge"**. Once approved, the run is finalized and saved into the historical SQLite database.

### 4️⃣ Commercial-Grade Developer Portal
* Navigate to **[http://localhost:8000/docs](http://localhost:8000/docs)** to view the customized Swagger/OpenAPI documentation, detailing the endpoints, authentication, and Google ADK orchestration architecture.
* Navigate to **[http://localhost:8001/](http://localhost:8001/)** or **[http://localhost:8002/](http://localhost:8002/)** in your browser to see custom, responsive landing pages designed for the standalone Model Context Protocol (MCP) servers.

---

## 📁 Technical Architecture Checklist

* **Orchestrator Logic**: Located in [Orchestrator/workflow.py](./Orchestrator/workflow.py) (uses Google ADK).
* **FastAPI Entry Point**: Located in [main.py](./main.py).
* **Model Context Protocol (MCP) Servers**: Located in the [mcp_servers/](./mcp_servers/) directory.
* **SQLite Database Schema**: Located in [database/schema.sql](./database/schema.sql).

Thank you for evaluating Business Guardian AI!

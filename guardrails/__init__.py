"""Guardrails package — security, validation, and observability layer.

Every guardrail module is called by the Orchestrator or the Evaluation
Agent.  Agents never call guardrails directly (except the Evaluation
Agent, which uses ``validation_guardrail`` and ``confidence_guardrail``
as its primary business logic).

Modules
-------
* ``audit_logger``          — structured event logging to file + SQLite
* ``hitl_guardrail``        — Human-In-The-Loop approval gate
* ``validation_guardrail``  — agent/MCP output schema validation
* ``confidence_guardrail``  — pipeline confidence scoring + escalation

Security principles (Google Secure Agentic Coding)
---------------------------------------------------
1. Input Validation       — every external input is type-checked
2. Output Validation      — every agent output is schema-validated
3. HITL Approval          — mandatory pause before external comms
4. Confidence Escalation  — low-confidence runs flagged for review
5. Audit Logging          — every action recorded to immutable log
6. Failure Isolation      — guardrail errors never crash the pipeline
7. Tool Access Governance — guardrails enforce scope boundaries
8. Safe Error Handling    — structured error responses, never raw traces
"""

"""Business Health Skill — weighted risk aggregation, trend analysis, and action prioritisation.

Consumed by
-----------
* ``risk_tracker_agent.py``  → ``compute_business_risk_score``, ``compute_risk_trend``
* ``strategy_agent.py``      → ``compute_business_health_score``, ``prioritize_actions``

Architecture alignment
----------------------
* ``compute_business_risk_score`` uses ``config.RISK_WEIGHTS`` for the weighted
  average instead of a simple arithmetic mean, matching the architecture's
  domain-importance model (Inventory/Finance 30 %, Supplier/Compliance 20 %).
* ``compute_risk_trend`` uses a ±5-point dead-band to avoid noise-driven
  oscillation between "improving" / "deteriorating".

Reference: ORCHESTRATOR_CONTRACT §5 (risk_trend), AGENT_CONTRACTS §5/§6.
"""

from __future__ import annotations

import logging
from typing import Any

from config import RISK_WEIGHTS_BY_SECTOR, CRITICAL_RISK_THRESHOLD

logger = logging.getLogger(__name__)


# ===================================================================
# Risk Aggregation  (used by risk_tracker_agent)
# ===================================================================

def compute_business_risk_score(
    inv_score: int,
    fin_score: int,
    sup_score: int,
    com_score: int,
    weights: dict[str, float] | None = None,
) -> int:
    """Compute the weighted aggregate Business Risk Score (0–100)."""
    inv = _clamp_input(inv_score)
    fin = _clamp_input(fin_score)
    sup = _clamp_input(sup_score)
    com = _clamp_input(com_score)

    w = weights if weights is not None else RISK_WEIGHTS_BY_SECTOR.get("retail", {})
    weighted = (
        inv * w.get("inventory", 0.25)
        + fin * w.get("finance", 0.25)
        + sup * w.get("supplier", 0.25)
        + com * w.get("compliance", 0.25)
    )

    return max(0, min(100, int(round(weighted))))


def compute_risk_trend(
    biz_risk_score: int,
    risk_history: list[dict[str, Any]],
) -> str:
    """Determine risk trajectory from the latest historical score.

    Uses a ±5-point dead-band around the previous score so that minor
    fluctuations don't generate misleading trend signals.

    Mapping (ORCHESTRATOR_CONTRACT §5 — risk_trend):
    * ``"deteriorating"`` — risk increased by more than 5 points
    * ``"improving"``     — risk decreased by more than 5 points
    * ``"stable"``        — change is within ±5 points, or no history

    Parameters
    ----------
    biz_risk_score:
        Current aggregate business risk score.
    risk_history:
        Chronologically ordered list of prior risk snapshots.  The last
        element is the most recent.  Each dict should contain a
        ``"business_risk_score"`` key.

    Returns
    -------
    str
        One of ``"improving"``, ``"stable"``, or ``"deteriorating"``.
    """
    if not risk_history:
        return "stable"

    # Walk backwards to find the most recent valid historical score
    last_score: int | None = None
    for entry in reversed(risk_history):
        val = entry.get("business_risk_score") if isinstance(entry, dict) else None
        if val is not None:
            try:
                last_score = int(val)
                break
            except (TypeError, ValueError):
                continue

    if last_score is None:
        return "stable"

    current = _clamp_input(biz_risk_score)
    delta = current - last_score

    if delta > 5:
        return "deteriorating"
    if delta < -5:
        return "improving"
    return "stable"


# ===================================================================
# Health Score  (used by strategy_agent)
# ===================================================================

def compute_business_health_score(risk_score: int) -> int:
    """Derive Business Health Score as the complement of the risk score.

    ``health = 100 − risk``, clamped to [0, 100].

    Parameters
    ----------
    risk_score:
        Aggregate business risk score (0–100).

    Returns
    -------
    int
        Health score in [0, 100].
    """
    return max(0, min(100, 100 - _clamp_input(risk_score)))


# ===================================================================
# Action Prioritisation  (used by strategy_agent)
# ===================================================================

def prioritize_actions(
    biz_risk_rep: dict[str, Any],
    inventory_rep: dict[str, Any],
    finance_rep: dict[str, Any],
    supplier_rep: dict[str, Any],
    compliance_rep: dict[str, Any],
    business_type: str,
) -> list[dict[str, str]]:
    """Extract and rank the top-3 recommended actions across all domains.

    Actions are scored internally by an *urgency weight* and then sorted
    in descending order.  The output always contains exactly 3 items so
    that the Strategy Agent contract is satisfied.

    Scoring heuristic (not exposed in output):
    * Overdue compliance      → weight 100
    * Negative profit margin  → weight 90
    * Imminent stockouts      → weight 80
    * High-risk suppliers     → weight 70
    * Domain risk ≥ threshold → weight 50
    * Generic fill items      → weight 10

    Parameters
    ----------
    biz_risk_rep:
        Full output from the Risk Tracker Agent.
    inventory_rep, finance_rep, supplier_rep, compliance_rep:
        Full outputs from the four domain agents.
    business_type:
        Business vertical (``"retail"``, ``"agriculture"``, ``"ecommerce"``).

    Returns
    -------
    list[dict]
        Exactly 3 action dicts, each containing: ``action_title``,
        ``action_description``, ``urgency``, ``expected_impact``,
        ``target_domain``, and ``rank``.
    """
    candidates: list[tuple[int, dict[str, str]]] = []  # (weight, action)

    # --- Compliance overdue -------------------------------------------
    comp = _safe_dict(compliance_rep)
    overdue = _safe_int(comp.get("overdue_count"), 0)
    if overdue > 0:
        candidates.append((100, {
            "action_title": "Resolve Overdue Compliance",
            "action_description": (
                f"Address {overdue} overdue obligation(s) immediately to "
                "avoid regulatory penalties and potential operational shutdown."
            ),
            "urgency": "immediate",
            "expected_impact": "Avoid legal penalties and operational shutdown",
            "target_domain": "compliance",
        }))

    # --- Finance negative margin --------------------------------------
    fin = _safe_dict(finance_rep)
    margin = _safe_float(fin.get("profit_margin"), 100.0)
    if margin < 0.0:
        candidates.append((90, {
            "action_title": "Address Negative Margins",
            "action_description": (
                f"Profit margin is {margin:.1f} %. Review pricing, cut overhead, "
                "and renegotiate vendor terms to restore profitability."
            ),
            "urgency": "immediate",
            "expected_impact": "Restore profitability and preserve cash runway",
            "target_domain": "finance",
        }))
    elif margin < 10.0:
        candidates.append((60, {
            "action_title": "Improve Thin Profit Margins",
            "action_description": (
                f"Profit margin is only {margin:.1f} %. Explore cost optimisation "
                "and new revenue channels to build a financial buffer."
            ),
            "urgency": "this_week",
            "expected_impact": "Strengthen financial resilience against market shocks",
            "target_domain": "finance",
        }))

    # --- Inventory imminent stockouts ---------------------------------
    inv = _safe_dict(inventory_rep)
    preds = inv.get("stockout_prediction") or []
    urgent_stockouts = [
        p for p in preds
        if _safe_int(p.get("days_until_stockout"), 999) < 7
    ]
    if urgent_stockouts:
        names = ", ".join(
            p.get("product_name", p.get("product_id", "?"))
            for p in urgent_stockouts[:3]
        )
        suffix = f" (+{len(urgent_stockouts) - 3} more)" if len(urgent_stockouts) > 3 else ""
        candidates.append((80, {
            "action_title": "Prevent Imminent Stockouts",
            "action_description": (
                f"Expedite reorders for {len(urgent_stockouts)} product(s) "
                f"at risk within 7 days: {names}{suffix}."
            ),
            "urgency": "this_week",
            "expected_impact": "Maintain sales volume and customer satisfaction",
            "target_domain": "inventory",
        }))

    # --- High-risk suppliers ------------------------------------------
    sup = _safe_dict(supplier_rep)
    high_risk = sup.get("high_risk_suppliers") or []
    if high_risk:
        names = ", ".join(s.get("supplier_name", "?") for s in high_risk[:3])
        candidates.append((70, {
            "action_title": "Mitigate High-Risk Suppliers",
            "action_description": (
                f"Engage backup vendors for {len(high_risk)} flagged "
                f"supplier(s): {names}. Monitor delivery metrics weekly."
            ),
            "urgency": "this_month",
            "expected_impact": "Ensure supply chain continuity",
            "target_domain": "supplier",
        }))

    # --- Business-type–specific recommendation ------------------------
    if business_type == "agriculture":
        spoilage_items = [
            p for p in preds
            if p.get("spoilage_risk") is True
        ]
        if spoilage_items:
            candidates.append((65, {
                "action_title": "Manage Spoilage Risk",
                "action_description": (
                    f"{len(spoilage_items)} product(s) have slow turnover "
                    "and may spoil before sale. Adjust procurement volumes."
                ),
                "urgency": "this_week",
                "expected_impact": "Reduce waste and protect margins",
                "target_domain": "inventory",
            }))

    # --- Generic fill actions (always available) ----------------------
    candidates.append((10, {
        "action_title": "Review Operational Efficiency",
        "action_description": (
            "Conduct a general review of current workflows to identify "
            "cost-saving opportunities and process improvements."
        ),
        "urgency": "this_month",
        "expected_impact": "Improve overall margins",
        "target_domain": "strategy",
    }))
    candidates.append((8, {
        "action_title": "Plan Quarterly Budget",
        "action_description": (
            "Realign quarterly spend with revenue forecasts to improve "
            "cash flow predictability."
        ),
        "urgency": "this_quarter",
        "expected_impact": "Better cash flow management",
        "target_domain": "finance",
    }))
    candidates.append((6, {
        "action_title": "Evaluate Expansion Channels",
        "action_description": (
            "Assess new sales channels and market segments to drive "
            "top-line revenue growth."
        ),
        "urgency": "this_quarter",
        "expected_impact": "Increased market share",
        "target_domain": "strategy",
    }))

    # --- Sort by weight (desc) and take top 3 -------------------------
    candidates.sort(key=lambda c: c[0], reverse=True)
    actions: list[dict[str, str]] = []
    for rank, (_, action) in enumerate(candidates[:3], start=1):
        action["rank"] = rank  # type: ignore[assignment]
        actions.append(action)

    return actions


# ===================================================================
# Internal helpers
# ===================================================================

def _clamp_input(value: Any) -> int:
    """Clamp a value to [0, 100] as int; defaults to 0 on bad input."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, v))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

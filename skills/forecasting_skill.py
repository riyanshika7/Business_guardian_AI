"""Forecasting Skill — unified 0–100 risk scoring for all four business domains.

Every function in this module converts raw business metrics into a
normalised integer risk score on the 0–100 scale (0 = no risk, 100 = max).

Scoring philosophy
------------------
*  Scores use *continuous* formulas where possible to avoid sudden jumps.
*  Edge cases (empty data, zero denominators, negative values) always
   return a safe default — never raise.
*  All outputs are clamped to ``[0, 100]``.

Consumed by
-----------
* ``inventory_agent.py``  → ``compute_inventory_risk_score``
* ``finance_agent.py``    → ``compute_finance_risk_score``
* ``supplier_agent.py``   → ``compute_supplier_risk_score``
* ``compliance_agent.py`` → ``compute_compliance_risk_score``

Reference: AGENT_CONTRACTS §1–§4 (risk score output fields).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ===================================================================
# Inventory Risk  (used by inventory_agent)
# ===================================================================

def compute_inventory_risk_score(
    stockout_preds: list[dict[str, Any]],
    reorder_recs: list[dict[str, Any]],
    num_products: int,
) -> int:
    """Compute inventory risk from stockout predictions and reorder volume.

    Scoring breakdown (additive, clamped 0–100):
    * Urgent stockout ratio   (< 7 days)  → up to 60 points
    * Near stockout ratio     (< 14 days) → up to 20 points
    * Reorder backlog ratio                → up to 20 points

    Parameters
    ----------
    stockout_preds:
        List of per-product stockout prediction dicts.
    reorder_recs:
        List of products that have breached their reorder point.
    num_products:
        Total active product count (denominator for ratios).

    Returns
    -------
    int
        Risk score in [0, 100].
    """
    if num_products <= 0:
        return 0

    # Count products by urgency band
    urgent = 0   # stock out within 7 days
    near = 0     # stock out within 14 days (but > 7)
    for pred in stockout_preds:
        days = _safe_int(pred.get("days_until_stockout"), 999)
        if days < 7:
            urgent += 1
        elif days < 14:
            near += 1

    # Ratio-based scoring to avoid sudden jumps
    urgent_ratio = urgent / num_products          # 0.0 – 1.0
    near_ratio = near / num_products
    reorder_ratio = len(reorder_recs) / num_products

    score = (
        urgent_ratio * 60.0
        + near_ratio * 20.0
        + reorder_ratio * 20.0
    )

    return _clamp(score)


# ===================================================================
# Finance Risk  (used by finance_agent)
# ===================================================================

def compute_finance_risk_score(
    profit_margin: float,
    net_profit: float,
    total_revenue: float,
) -> int:
    """Compute finance risk from margin and revenue health.

    Uses a continuous piece-wise linear model rather than hard thresholds
    so that a margin of 9.9 % and 10.1 % don't produce a 30-point gap.

    Scoring bands:
    * margin < 0       → 75 + penalty up to 100  (loss severity)
    * 0 ≤ margin < 10  → 40 – 75  (thin margins)
    * 10 ≤ margin < 25 → 10 – 40  (moderate)
    * margin ≥ 25      → 5 – 10   (healthy)

    An additional +10 penalty applies when ``total_revenue`` is zero
    (no sales at all).

    Parameters
    ----------
    profit_margin:
        Profit as a percentage of revenue.
    net_profit:
        Absolute profit/loss value.
    total_revenue:
        Total revenue over the analysis period.

    Returns
    -------
    int
        Risk score in [0, 100].
    """
    margin = _safe_float(profit_margin, 0.0)
    revenue = _safe_float(total_revenue, 0.0)

    if revenue <= 0.0:
        return 100  # No revenue is maximum risk

    if margin < 0.0:
        # Loss severity: deeper loss → higher score (75–100)
        penalty = min(25.0, abs(margin) * 0.5)
        score = 75.0 + penalty
    elif margin < 10.0:
        # Thin margins: linear 75 → 40 as margin goes 0 → 10
        score = 75.0 - (margin / 10.0) * 35.0
    elif margin < 25.0:
        # Moderate: linear 40 → 10 as margin goes 10 → 25
        score = 40.0 - ((margin - 10.0) / 15.0) * 30.0
    else:
        # Healthy: linear 10 → 5 as margin goes 25 → 50+
        score = max(5.0, 10.0 - ((margin - 25.0) / 25.0) * 5.0)

    return _clamp(score)


# ===================================================================
# Supplier Risk  (used by supplier_agent)
# ===================================================================

def compute_supplier_risk_score(
    high_risk_suppliers: list[dict[str, Any]],
    dependency_score: int,
) -> int:
    """Compute supplier risk from vendor concentration and flagged suppliers.

    Scoring breakdown (additive, clamped 0–100):
    * Dependency concentration  → up to 50 points  (linear from 0–100 %)
    * High-risk supplier count  → 15 points each, capped at 50

    Parameters
    ----------
    high_risk_suppliers:
        List of suppliers flagged as high/medium risk.
    dependency_score:
        Maximum single-supplier dependency percentage (0–100).

    Returns
    -------
    int
        Risk score in [0, 100].
    """
    dep = _clamp_float(_safe_float(dependency_score, 0.0), 0.0, 100.0)

    # Dependency: 0–100 % maps linearly to 0–50 points
    dep_component = dep * 0.50

    # Each high-risk supplier adds 15 points, capped at 50
    hr_count = len(high_risk_suppliers) if high_risk_suppliers else 0
    hr_component = min(50.0, hr_count * 15.0)

    score = dep_component + hr_component
    return _clamp(score)


# ===================================================================
# Compliance Risk  (used by compliance_agent)
# ===================================================================

def compute_compliance_risk_score(
    overdue_count: int,
    due_soon_count: int,
    total_events: int,
) -> int:
    """Compute compliance risk from obligation status distribution.

    Scoring breakdown (additive, clamped 0–100):
    * Each overdue event     → 30 points  (severe regulatory exposure)
    * Each due-soon event    → 10 points  (approaching deadline)
    * Baseline when total=0  → 0          (no obligations = no risk)

    Parameters
    ----------
    overdue_count:
        Number of obligations past their due date.
    due_soon_count:
        Number of obligations due within the analysis window.
    total_events:
        Total tracked compliance events (used for context only).

    Returns
    -------
    int
        Risk score in [0, 100].
    """
    if _safe_int(total_events, 0) == 0:
        return 0

    overdue = max(0, _safe_int(overdue_count, 0))
    soon = max(0, _safe_int(due_soon_count, 0))

    score = (overdue * 30.0) + (soon * 10.0)
    return _clamp(score)


# ===================================================================
# Internal helpers
# ===================================================================

def _safe_int(value: Any, default: int = 0) -> int:
    """Convert *value* to int, returning *default* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert *value* to float, returning *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(score: float, lo: int = 0, hi: int = 100) -> int:
    """Clamp *score* to ``[lo, hi]`` and cast to int."""
    return max(lo, min(hi, int(score)))


def _clamp_float(value: float, lo: float, hi: float) -> float:
    """Clamp a float to ``[lo, hi]``."""
    return max(lo, min(hi, value))

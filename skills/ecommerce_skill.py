"""E-Commerce Skill — domain-specific risk and sales analytics for online retail.

Provides return-rate risk assessment and channel performance utilities
tuned for e-commerce businesses where product returns, fulfilment speed,
and channel concentration are key operational risks.

Consumed by agents when ``business_type == "ecommerce"``.

Public API (signatures frozen — do not change)
----------------------------------------------
* ``assess_return_risk(total_sales, total_returns)``

Reference: AGENT_CONTRACTS §1–§3 (risk score fields).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Return-rate threshold bands (industry benchmarks).
_RETURN_RATE_CRITICAL: float = 0.15   # > 15 % return rate
_RETURN_RATE_HIGH: float = 0.10       # > 10 %
_RETURN_RATE_MODERATE: float = 0.05   # > 5 %


# ===================================================================
# Return Risk Assessment
# ===================================================================

def assess_return_risk(
    total_sales: int | float,
    total_returns: int | float,
) -> int:
    """Score the operational risk arising from product return rates.

    Uses a continuous piece-wise linear model so that small changes in
    return rate don't produce sudden score jumps.

    Scoring bands:
    * return_rate ≥ 15 %  → 80 – 100  (critical)
    * 10 % – 15 %         → 50 – 80   (high)
    * 5 %  – 10 %         → 20 – 50   (moderate)
    * < 5 %               → 5 – 20    (healthy)
    * No sales / bad data → 0         (no signal)

    Parameters
    ----------
    total_sales:
        Total number of units sold (or total order count).
    total_returns:
        Total number of units returned (or total return count).

    Returns
    -------
    int
        Risk score in [0, 100].
    """
    sales = _safe_float(total_sales, 0.0)
    returns = _safe_float(total_returns, 0.0)

    if sales <= 0.0:
        return 0   # No sales → no signal to score against

    return_rate = max(0.0, returns) / sales

    if return_rate >= _RETURN_RATE_CRITICAL:
        # 80–100: linear scale for rates above 15 %, capped at 30 %
        excess = min(return_rate - _RETURN_RATE_CRITICAL, 0.15)
        score = 80.0 + (excess / 0.15) * 20.0
    elif return_rate >= _RETURN_RATE_HIGH:
        # 50–80: linear between 10 %–15 %
        ratio = (return_rate - _RETURN_RATE_HIGH) / (_RETURN_RATE_CRITICAL - _RETURN_RATE_HIGH)
        score = 50.0 + ratio * 30.0
    elif return_rate >= _RETURN_RATE_MODERATE:
        # 20–50: linear between 5 %–10 %
        ratio = (return_rate - _RETURN_RATE_MODERATE) / (_RETURN_RATE_HIGH - _RETURN_RATE_MODERATE)
        score = 20.0 + ratio * 30.0
    else:
        # 5–20: linear between 0 %–5 %
        ratio = return_rate / _RETURN_RATE_MODERATE
        score = 5.0 + ratio * 15.0

    return max(0, min(100, int(score)))


# ===================================================================
# Channel Concentration Risk  (utility — available for future agents)
# ===================================================================

def assess_channel_concentration(
    channel_revenues: dict[str, float],
) -> int:
    """Score risk from over-dependence on a single sales channel.

    A Herfindahl-style index: higher concentration → higher risk.

    Parameters
    ----------
    channel_revenues:
        Mapping of channel name → total revenue for the period.
        Example: ``{"website": 80000, "marketplace": 15000, "wholesale": 5000}``

    Returns
    -------
    int
        Concentration risk score in [0, 100].  0 if no data.
    """
    if not channel_revenues:
        return 0

    values = [max(0.0, _safe_float(v, 0.0)) for v in channel_revenues.values()]
    total = sum(values)
    if total <= 0.0:
        return 0

    shares = [v / total for v in values]
    hhi = sum(s ** 2 for s in shares)  # 1/N (perfect split) to 1.0 (monopoly)

    # Map HHI to 0–100.  Single-channel (HHI=1.0) → 100.
    # Two equal channels (HHI=0.5) → ~50.  Many channels → low.
    score = hhi * 100.0
    return max(0, min(100, int(score)))


# ===================================================================
# Internal helpers
# ===================================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

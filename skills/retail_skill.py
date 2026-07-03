"""Retail Skill — domain-specific inventory forecasting for retail businesses.

Provides stockout prediction and reorder recommendation logic tuned for
traditional retail with steady-state demand patterns.

Consumed by ``inventory_agent.py`` when ``business_type == "retail"``.

Public API (signatures frozen — do not change)
----------------------------------------------
* ``build_stockout_predictions(products, inventory, sales, window_days)``
* ``build_reorder_recommendations(products, inventory, stockout_preds)``

Reference: AGENT_CONTRACTS §1 — Inventory Agent output schema.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ===================================================================
# Stockout Predictions
# ===================================================================

def build_stockout_predictions(
    products: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    sales: list[dict[str, Any]],
    window_days: int,
) -> list[dict[str, Any]]:
    """Predict days-until-stockout for every active product.

    Algorithm
    ---------
    1. Aggregate total units sold per product over the analysis window.
    2. Derive daily sales velocity = total_sold / window_days.
    3. Days until stockout  = current_stock / daily_velocity.
    4. Products with zero velocity get ``999`` (effectively infinite).

    Parameters
    ----------
    products:
        Product catalog records (need ``product_id``, ``product_name``).
    inventory:
        Current stock levels (need ``product_id``, ``current_stock``).
    sales:
        Sales transactions over the analysis window (need ``product_id``,
        ``quantity_sold`` or ``quantity``).
    window_days:
        Number of days the sales data covers (must be > 0).

    Returns
    -------
    list[dict]
        One prediction dict per product with keys: ``product_id``,
        ``product_name``, ``current_stock``, ``daily_velocity``,
        ``days_until_stockout``.
    """
    # Guard: empty inputs
    if not products:
        return []
    effective_window = max(1, _safe_int(window_days, 30))

    # Map current stock by product_id
    inv_map: dict[str, int] = {}
    for item in (inventory or []):
        pid = item.get("product_id")
        if pid is not None:
            inv_map[pid] = _safe_int(item.get("current_stock"), 0)

    # Aggregate sales volume per product
    sales_map: dict[str, float] = {}
    for sale in (sales or []):
        pid = sale.get("product_id")
        if pid is None:
            continue
        # Accept both "quantity_sold" (schema) and "quantity" (legacy)
        qty = _safe_float(
            sale.get("quantity_sold", sale.get("quantity", 0)),
            0.0,
        )
        sales_map[pid] = sales_map.get(pid, 0.0) + qty

    predictions: list[dict[str, Any]] = []
    for prod in products:
        pid = prod.get("product_id")
        if pid is None:
            continue

        stock = inv_map.get(pid, 0)
        total_sold = sales_map.get(pid, 0.0)
        velocity = total_sold / effective_window  # units / day

        if velocity > 0:
            days_until = int(stock / velocity)
        else:
            days_until = 999  # no recent sales → no imminent stockout

        predictions.append({
            "product_id": pid,
            "product_name": prod.get("product_name", "Unknown"),
            "current_stock": stock,
            "daily_velocity": round(velocity, 2),
            "days_until_stockout": days_until,
        })

    return predictions


# ===================================================================
# Reorder Recommendations
# ===================================================================

def build_reorder_recommendations(
    products: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    stockout_preds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Identify products that have breached their reorder point.

    Urgency classification:
    * ``"critical"`` — stock is **zero**
    * ``"high"``     — stock is > 0 but ≤ 50 % of reorder point
    * ``"medium"``   — stock is > 50 % of reorder point but still ≤ reorder point

    Parameters
    ----------
    products:
        Product catalog (need ``product_id``, ``product_name``,
        ``reorder_point``, ``reorder_quantity``).
    inventory:
        Current stock levels (used as fallback if predictions are sparse).
    stockout_preds:
        Output from ``build_stockout_predictions``.

    Returns
    -------
    list[dict]
        Reorder recommendation dicts for products below their reorder
        point, sorted by urgency (critical → high → medium).
    """
    if not products:
        return []

    pred_map: dict[str, dict[str, Any]] = {
        p["product_id"]: p for p in (stockout_preds or []) if "product_id" in p
    }

    urgency_order = {"critical": 0, "high": 1, "medium": 2}
    recs: list[dict[str, Any]] = []

    for prod in products:
        pid = prod.get("product_id")
        if pid is None:
            continue

        reorder_pt = _safe_int(prod.get("reorder_point"), 0)
        reorder_qty = _safe_int(prod.get("reorder_quantity"), 0)
        pred = pred_map.get(pid, {})
        stock = _safe_int(pred.get("current_stock"), 0)

        if stock > reorder_pt:
            continue  # Healthy stock level — skip

        # Classify urgency
        if stock == 0:
            urgency = "critical"
        elif reorder_pt > 0 and stock <= reorder_pt * 0.5:
            urgency = "high"
        else:
            urgency = "medium"

        name = prod.get("product_name", "Unknown")
        velocity = pred.get("daily_velocity", 0.0)

        recs.append({
            "product_id": pid,
            "product_name": name,
            "current_stock": stock,
            "reorder_point": reorder_pt,
            "reorder_quantity": reorder_qty,
            "urgency": urgency,
            "recommended_action": (
                f"Reorder {reorder_qty} units of '{name}'. "
                f"Stock ({stock}) is below reorder point ({reorder_pt}). "
                f"Daily velocity: {velocity} units/day."
            ),
        })

    # Sort by urgency severity
    recs.sort(key=lambda r: urgency_order.get(r.get("urgency", "medium"), 9))
    return recs


# ===================================================================
# Internal helpers
# ===================================================================

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

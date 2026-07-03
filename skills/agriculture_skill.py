"""Agriculture Skill — domain-specific inventory forecasting for agricultural businesses.

Extends the base retail logic with agriculture-sector concerns:
* **Spoilage risk** — perishable goods with slow turnover are flagged.
* **Seasonality awareness** — planting/harvest language in recommendations.

Consumed by ``inventory_agent.py`` when ``business_type == "agriculture"``.

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

# Spoilage thresholds (days).  If a product's projected days-to-stockout
# exceeds this value the product is turning over so slowly that spoilage
# becomes a concern for perishable agricultural goods.
_SPOILAGE_SLOW_TURNOVER_DAYS: int = 30
_SPOILAGE_HIGH_RISK_DAYS: int = 60


# ===================================================================
# Stockout Predictions  (agriculture variant)
# ===================================================================

def build_stockout_predictions(
    products: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    sales: list[dict[str, Any]],
    window_days: int,
) -> list[dict[str, Any]]:
    """Predict days-until-stockout with an agriculture spoilage overlay.

    Core algorithm is identical to ``retail_skill``.  Additionally, each
    prediction is annotated with:

    * ``spoilage_risk`` (bool)  — ``True`` when the product's projected
      days-to-stockout exceeds ``_SPOILAGE_SLOW_TURNOVER_DAYS``,
      indicating the stock may spoil before it sells.
    * ``spoilage_severity`` (str) — ``"high"`` if > 60 days, ``"medium"``
      if > 30 days, ``None`` otherwise.

    Parameters
    ----------
    products:
        Product catalog records.
    inventory:
        Current stock levels.
    sales:
        Sales transactions over the analysis window.
    window_days:
        Number of days the sales data covers (must be > 0).

    Returns
    -------
    list[dict]
        Per-product prediction dicts (retail fields + spoilage fields).
    """
    if not products:
        return []
    effective_window = max(1, _safe_int(window_days, 30))

    # Map current stock
    inv_map: dict[str, int] = {}
    for item in (inventory or []):
        pid = item.get("product_id")
        if pid is not None:
            inv_map[pid] = _safe_int(item.get("current_stock"), 0)

    # Aggregate sales
    sales_map: dict[str, float] = {}
    for sale in (sales or []):
        pid = sale.get("product_id")
        if pid is None:
            continue
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
        velocity = total_sold / effective_window

        if velocity > 0:
            days_until = int(stock / velocity)
        else:
            days_until = 999

        # Agriculture spoilage overlay
        spoilage_risk = days_until > _SPOILAGE_SLOW_TURNOVER_DAYS and stock > 0
        spoilage_severity: str | None = None
        if spoilage_risk:
            spoilage_severity = (
                "high" if days_until > _SPOILAGE_HIGH_RISK_DAYS else "medium"
            )

        predictions.append({
            "product_id": pid,
            "product_name": prod.get("product_name", "Unknown"),
            "current_stock": stock,
            "daily_velocity": round(velocity, 2),
            "days_until_stockout": days_until,
            "spoilage_risk": spoilage_risk,
            "spoilage_severity": spoilage_severity,
        })

    return predictions


# ===================================================================
# Reorder Recommendations  (agriculture variant)
# ===================================================================

def build_reorder_recommendations(
    products: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    stockout_preds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate reorder recommendations with agriculture-tuned language.

    Urgency classification mirrors ``retail_skill`` but recommendation
    text uses planting / procurement language appropriate for agricultural
    supply chains.

    Parameters
    ----------
    products:
        Product catalog (need ``product_id``, ``reorder_point``).
    inventory:
        Current stock levels (fallback source).
    stockout_preds:
        Output from ``build_stockout_predictions``.

    Returns
    -------
    list[dict]
        Reorder recommendations sorted by urgency.
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
            continue

        # Classify urgency
        if stock == 0:
            urgency = "critical"
        elif reorder_pt > 0 and stock <= reorder_pt * 0.5:
            urgency = "high"
        else:
            urgency = "medium"

        name = prod.get("product_name", "Unknown")
        spoilage = pred.get("spoilage_risk", False)

        action_text = (
            f"Schedule planting or procurement for '{name}'. "
            f"Stock ({stock}) is below reorder point ({reorder_pt})."
        )
        if spoilage:
            action_text += (
                " ⚠ Existing stock shows spoilage risk due to low turnover — "
                "consider smaller batch orders."
            )

        recs.append({
            "product_id": pid,
            "product_name": name,
            "current_stock": stock,
            "reorder_point": reorder_pt,
            "reorder_quantity": reorder_qty,
            "urgency": urgency,
            "spoilage_risk": spoilage,
            "recommended_action": action_text,
        })

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

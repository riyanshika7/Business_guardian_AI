from __future__ import annotations
from pydantic import BaseModel, Field

class Product(BaseModel):
    product_id: str
    product_name: str
    category: str
    sku: str | None = None
    unit_cost: float = Field(..., ge=0.0)
    unit_price: float = Field(..., ge=0.0)
    reorder_point: int = Field(..., ge=0)
    reorder_quantity: int = Field(..., gt=0)
    supplier_id: str | None = None
    is_active: bool
    created_at: str

class InventoryRecord(BaseModel):
    inventory_id: str
    product_id: str
    current_stock: int = Field(..., ge=0)
    warehouse_location: str | None = None
    last_updated: str
    recorded_by: str

class SalesRecord(BaseModel):
    sale_id: str
    product_id: str
    quantity_sold: int = Field(..., gt=0)
    sale_amount: float = Field(..., gt=0.0)
    unit_price_at_sale: float = Field(..., ge=0.0)
    sale_date: str
    channel: str | None = None
    recorded_at: str

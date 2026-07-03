from __future__ import annotations
from pydantic import BaseModel, Field

class SupplierRecord(BaseModel):
    """Represents a business supplier in the system."""
    supplier_id: str = Field(description="Unique supplier identifier")
    supplier_name: str = Field(description="Legal or trading name of the supplier")
    contact_name: str | None = Field(default=None, description="Primary contact person at the supplier")
    contact_email: str | None = Field(default=None, description="Primary contact email address")
    country: str = Field(description="Country where the supplier is based")
    product_categories: list[str] = Field(description="Categories of products supplied by the vendor")
    dependency_percentage: float | None = Field(default=None, ge=0.0, le=100.0, description="Percentage of total purchases from this supplier")
    contract_start_date: str | None = Field(default=None, description="Start date of current supplier contract (YYYY-MM-DD)")
    contract_end_date: str | None = Field(default=None, description="End date of current supplier contract (YYYY-MM-DD)")
    is_active: bool = Field(description="Whether this supplier is currently active")
    created_at: str = Field(description="Record creation timestamp")

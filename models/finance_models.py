from __future__ import annotations
from pydantic import BaseModel, Field

class ExpenseRecord(BaseModel):
    """Represents a single business expense entry in the finance domain."""
    expense_id: str = Field(description="Unique expense identifier")
    expense_category: str = Field(description="Category of the expense")
    amount: float = Field(..., gt=0.0, description="Expense amount, must be > 0")
    description: str | None = Field(default=None, description="Detailed description of the expense")
    expense_date: str = Field(description="Date when the expense was incurred (YYYY-MM-DD)")
    vendor: str | None = Field(default=None, description="Name of the vendor paid")
    recorded_at: str = Field(description="Timestamp when the record was created")

from __future__ import annotations
from pydantic import BaseModel, Field

class ComplianceEvent(BaseModel):
    """Represents a compliance obligation, regulatory requirement, or contract renewal event."""
    event_id: str = Field(description="Unique compliance event identifier")
    event_name: str = Field(description="Name of the compliance obligation (e.g., 'GST Filing Q1')")
    event_type: str = Field(description="Type of obligation: 'tax', 'license', 'insurance', 'regulatory', 'contract_renewal', or 'other'")
    due_date: str = Field(description="Date by which the obligation must be fulfilled (YYYY-MM-DD)")
    description: str | None = Field(default=None, description="Detailed description of the compliance obligation")
    responsible_party: str | None = Field(default=None, description="Person or role responsible for this obligation")
    status: str = Field(description="Current execution status: 'pending', 'completed', or 'overdue'")
    recurrence: str | None = Field(default=None, description="Recurrence pattern: 'monthly', 'quarterly', 'annual', or 'one_time'")
    created_at: str = Field(description="Record creation timestamp")

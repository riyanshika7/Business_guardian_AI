from __future__ import annotations
from pydantic import BaseModel, Field

class RiskScore(BaseModel):
    """Represents a single risk score record in the system."""
    score_id: str = Field(description="Unique risk score record identifier")
    agent_name: str = Field(description="Name of the agent that produced this score")
    score_type: str = Field(description="Type of score (e.g., 'inventory_risk', 'finance_risk')")
    score_value: int = Field(..., ge=0, le=100, description="The numeric score value, must be 0 to 100")
    run_id: str = Field(description="Identifier linking this score to a specific analysis run")
    recorded_at: str = Field(description="Timestamp when this score was recorded")

class CriticalRisk(BaseModel):
    """Represents details of a critical risk identified in a domain."""
    domain: str = Field(description="The domain of the critical risk")
    score: int = Field(..., ge=0, le=100, description="Risk score value")
    severity: str = Field(description="Severity level: 'critical', 'high', or 'medium'")

class RiskBreakdown(BaseModel):
    """Weighted contribution of each domain risk."""
    inventory_risk_score: int = Field(..., ge=0, le=100)
    finance_risk_score: int = Field(..., ge=0, le=100)
    supplier_risk_score: int = Field(..., ge=0, le=100)
    compliance_risk_score: int = Field(..., ge=0, le=100)

class BusinessRiskReport(BaseModel):
    """Complete output schema of the Risk Tracker Agent."""
    agent: str = Field(default="risk_tracker_agent", description="Always 'risk_tracker_agent'")
    business_risk_score: int = Field(..., ge=0, le=100, description="Aggregate business risk score")
    risk_breakdown: RiskBreakdown = Field(description="Weighted contribution of each domain risk")
    risk_trend: str = Field(description="Trend direction: 'improving', 'stable', or 'deteriorating'")
    critical_risks: list[CriticalRisk] = Field(description="List of risk areas scoring above 70")
    status: str = Field(description="Status of the report: 'success' or 'error'")
    timestamp: str = Field(description="ISO 8601 timestamp of the report generation")

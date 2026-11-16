from pydantic import BaseModel
from datetime import date
from uuid import UUID
from typing import Optional

class ObligationOut(BaseModel):
    id: UUID
    agreement_id: UUID
    obligation_type: str
    status: str
    due_date: Optional[date]
    assignee: Optional[UUID]
    model_config = {"from_attributes": True}

class RiskOut(BaseModel):
    id: UUID
    agreement_id: UUID
    risk_type: str
    severity: int
    description: Optional[str]
    model_config = {"from_attributes": True}
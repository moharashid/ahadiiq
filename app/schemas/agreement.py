from pydantic import BaseModel
from datetime import date
from uuid import UUID
from typing import Optional
from typing import Any, Optional

class AgreementOut(BaseModel):
    id: UUID
    filename: str
    agreement_type: Optional[str] = None
    status: str
    risk_level: Optional[str] = None
    risk_score: Optional[int] = None
    expiry_date: Optional[date] = None
    parties: Optional[Any] = None
    signatories: Optional[Any] = None
    model_config = {"from_attributes": True}
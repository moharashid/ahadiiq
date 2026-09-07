from app.core.database import Base
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text, Float, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Clause(Base):
    __tablename__ = "clauses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    agreement_id = Column(UUID(as_uuid=True), ForeignKey("agreements.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    clause_text = Column(Text, nullable=False)
    clause_type = Column(String(50), nullable=True) 
    status = Column(String(50), nullable=False, default="extracted") 
    notice_period = Column(Integer, nullable=True)
    relative_to = Column(String(50), nullable=True)
    amount = Column(Numeric(precision=10, scale=2), nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
from app.core.database import Base
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Risk(Base):
    __tablename__ = "risks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    agreement_id = Column(UUID(as_uuid=True), ForeignKey("agreements.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    clause_id = Column(UUID(as_uuid=True), ForeignKey("clauses.id"), nullable=True)
    risk_type = Column(String(50), nullable=False)
    severity = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
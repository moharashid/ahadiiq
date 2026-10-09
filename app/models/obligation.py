from app.core.database import Base
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text, Float, Integer, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Obligation(Base):
    __tablename__ = "obligations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    agreement_id = Column(UUID(as_uuid=True), ForeignKey("agreements.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    clause_id = Column(UUID(as_uuid=True), ForeignKey("clauses.id"), nullable=True)
    obligation_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    due_date = Column(Date, nullable=True)
    assignee = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
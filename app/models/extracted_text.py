from app.core.database import Base
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID
import uuid

class ExtractedText(Base):
    __tablename__ = "extracted_texts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = Column(UUID(as_uuid=True), ForeignKey("agreements.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    extracted_text = Column(Text, nullable=False)
    job_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confidence_score = Column(Float, nullable=True)
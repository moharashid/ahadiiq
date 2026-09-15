from app.core.database import Base
from sqlalchemy import Column, String, DateTime, func, ForeignKey,Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


class Agreement(Base):
    __tablename__ = "agreements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    storage_key = Column(String(255), nullable = False)
    agreement_type = Column(String(50), nullable=True)
    status = Column(String(50), nullable = False, default="uploaded")
    owner_id = Column(UUID(as_uuid = True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid = True), ForeignKey("tenants.id"), nullable = False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    parties = Column(JSONB, nullable=True)
    signatories = Column(JSONB, nullable=True)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    
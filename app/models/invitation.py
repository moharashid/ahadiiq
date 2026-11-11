from app.core.database import Base
from sqlalchemy import Column, String, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Invitation(Base):
    __tablename__ = "invitations"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token       = Column(String(255), unique=True, index=True, nullable=False)   # the secret in the invite link
    email       = Column(String(255), nullable=False)                            # who it's for
    tenant_id   = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    role        = Column(String(50), nullable=False)                             # what they become: admin | member
    status      = Column(String(50), nullable=False, default="pending")          # pending | accepted | revoked
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
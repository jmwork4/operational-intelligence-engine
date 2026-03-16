"""AuditLog model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class AuditLog(TenantMixin, Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        sa.Index("ix_audit_logs_tenant_created_at", "tenant_id", "created_at"),
    )

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    user_id: Mapped[sa.Uuid | None] = mapped_column(sa.Uuid, nullable=True)
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

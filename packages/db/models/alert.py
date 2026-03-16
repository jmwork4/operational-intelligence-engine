"""Alert model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import AuditMixin, Base


class Alert(AuditMixin, Base):
    __tablename__ = "alerts"

    __table_args__ = (
        sa.UniqueConstraint("tenant_id", "dedup_key", name="uq_alerts_tenant_dedup"),
    )

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    rule_id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(20), default="active", nullable=False
    )
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    dedup_key: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    acknowledged_by: Mapped[sa.Uuid | None] = mapped_column(sa.Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

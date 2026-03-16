"""Event model — central operational log."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class Event(TenantMixin, Base):
    __tablename__ = "events"

    __table_args__ = (
        sa.Index("ix_events_tenant_event_type", "tenant_id", "event_type"),
        sa.Index("ix_events_tenant_entity_id", "tenant_id", "entity_id"),
        sa.Index("ix_events_tenant_occurred_at", "tenant_id", "occurred_at"),
    )

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    event_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    process_id: Mapped[sa.Uuid | None] = mapped_column(sa.Uuid, nullable=True)
    resource_id: Mapped[sa.Uuid | None] = mapped_column(sa.Uuid, nullable=True)
    source_system: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    trace_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

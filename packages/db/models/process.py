"""Process model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import AuditMixin, Base


class Process(AuditMixin, Base):
    __tablename__ = "processes"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    process_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

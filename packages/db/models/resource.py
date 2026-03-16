"""Resource model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import AuditMixin, Base


class Resource(AuditMixin, Base):
    __tablename__ = "resources"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    resource_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

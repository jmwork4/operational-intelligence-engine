"""Tenant model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    plan_tier: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    settings: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

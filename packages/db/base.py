"""SQLAlchemy declarative base and common mixins."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""

    pass


class TimestampMixin:
    """Adds created_at and updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )


class TenantMixin:
    """Adds tenant_id column with FK to tenants.id."""

    tenant_id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class AuditMixin(TenantMixin, TimestampMixin):
    """Combines TenantMixin and TimestampMixin."""

    pass

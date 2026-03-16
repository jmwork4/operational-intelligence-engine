"""User model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import AuditMixin, Base


class User(AuditMixin, Base):
    __tablename__ = "users"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(sa.String(320), nullable=False)
    hashed_password: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

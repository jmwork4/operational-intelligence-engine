"""Rule model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import AuditMixin, Base


class Rule(AuditMixin, Base):
    __tablename__ = "rules"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    rule_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    trigger_event: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    condition_expression: Mapped[str] = mapped_column(sa.Text, nullable=False)
    evaluation_window: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    severity: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    action_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

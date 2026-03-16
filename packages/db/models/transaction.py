"""Transaction model."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import AuditMixin, Base


class Transaction(AuditMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    process_id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, sa.ForeignKey("processes.id", ondelete="CASCADE"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(sa.Numeric, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

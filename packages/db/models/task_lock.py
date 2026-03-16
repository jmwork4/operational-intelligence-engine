"""TaskExecutionLock model."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base


class TaskExecutionLock(Base):
    __tablename__ = "task_execution_locks"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    task_name: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    locked_by: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    locked_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

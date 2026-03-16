"""PromptTemplate and PromptEvaluation models."""

from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    task_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    model_family: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    system_prompt: Mapped[str] = mapped_column(sa.Text, nullable=False)
    user_template: Mapped[str] = mapped_column(sa.Text, nullable=False)
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evaluation_set_reference: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


class PromptEvaluation(Base):
    __tablename__ = "prompt_evaluations"

    id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid4
    )
    prompt_template_id: Mapped[sa.Uuid] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_example: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evaluation_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

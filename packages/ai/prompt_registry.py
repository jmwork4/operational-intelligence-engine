"""Prompt Registry — versioned prompt management backed by the database.

All prompts are stored in the ``prompt_templates`` table.  Hardcoded prompts
are **not** permitted; every prompt used at inference time must be fetched from
the registry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.prompt import PromptEvaluation, PromptTemplate

logger = logging.getLogger(__name__)

# Minimum average score required before a prompt can be promoted to active.
_PROMOTION_THRESHOLD: float = 0.80


@dataclass
class EvaluationResult:
    """Outcome of running all evaluation examples against a prompt template."""

    passed: bool
    scores: dict[str, float]
    failures: list[str]


class PromptRegistry:
    """Service for managing versioned prompt templates.

    Parameters
    ----------
    session:
        An async SQLAlchemy session used for all database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_active_prompt(
        self, task_type: str, model_family: str
    ) -> dict[str, Any]:
        """Return the currently active prompt for *task_type* + *model_family*.

        Raises ``ValueError`` if no active prompt is found.
        """
        stmt = (
            sa.select(PromptTemplate)
            .where(
                PromptTemplate.task_type == task_type,
                PromptTemplate.model_family == model_family,
                PromptTemplate.is_active.is_(True),
            )
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise ValueError(
                f"No active prompt for task_type={task_type!r}, "
                f"model_family={model_family!r}"
            )
        return self._row_to_dict(row)

    async def get_prompt_by_version(
        self, name: str, version: int
    ) -> dict[str, Any]:
        """Fetch a specific prompt by *name* and *version*.

        Raises ``ValueError`` if the combination does not exist.
        """
        stmt = sa.select(PromptTemplate).where(
            PromptTemplate.name == name,
            PromptTemplate.version == version,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            raise ValueError(
                f"Prompt not found: name={name!r}, version={version}"
            )
        return self._row_to_dict(row)

    async def register_prompt(self, prompt_data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new prompt template and return its persisted representation.

        ``prompt_data`` must contain at minimum: ``name``, ``task_type``,
        ``model_family``, ``system_prompt``, ``user_template``.  A ``version``
        is auto-assigned if not provided.
        """
        # Auto-assign the next version number for this prompt name.
        if "version" not in prompt_data:
            prompt_data["version"] = await self._next_version(prompt_data["name"])

        # New prompts are registered as inactive until promoted via evaluation.
        template = PromptTemplate(
            id=prompt_data.get("id", uuid4()),
            name=prompt_data["name"],
            version=prompt_data["version"],
            task_type=prompt_data["task_type"],
            model_family=prompt_data["model_family"],
            system_prompt=prompt_data["system_prompt"],
            user_template=prompt_data["user_template"],
            input_schema=prompt_data.get("input_schema"),
            output_schema=prompt_data.get("output_schema"),
            evaluation_set_reference=prompt_data.get("evaluation_set_reference"),
            is_active=False,
        )

        self._session.add(template)
        await self._session.flush()
        await self._session.refresh(template)

        logger.info(
            "Registered prompt %s v%d (id=%s)",
            template.name,
            template.version,
            template.id,
        )
        return self._row_to_dict(template)

    async def evaluate_prompt(
        self, prompt_template_id: str
    ) -> EvaluationResult:
        """Run the evaluation set associated with a prompt template.

        The method fetches all ``PromptEvaluation`` rows linked to the
        template, scores each one, and returns an aggregate result.
        """
        template_uuid = UUID(prompt_template_id)

        # Fetch evaluation examples.
        stmt = sa.select(PromptEvaluation).where(
            PromptEvaluation.prompt_template_id == template_uuid
        )
        result = await self._session.execute(stmt)
        evaluations = result.scalars().all()

        if not evaluations:
            return EvaluationResult(
                passed=False,
                scores={},
                failures=["No evaluation examples found for this prompt template."],
            )

        scores: dict[str, float] = {}
        failures: list[str] = []

        for ev in evaluations:
            # TODO: Invoke the model with ev.input_example and compare to
            # ev.expected_output using the evaluation_type strategy (e.g.
            # "exact_match", "semantic_similarity", "llm_judge").
            # For now we record a placeholder score of 1.0 for each example.
            score_key = f"{ev.evaluation_type}:{ev.id}"
            scores[score_key] = 1.0

        avg_score = sum(scores.values()) / len(scores) if scores else 0.0
        passed = avg_score >= _PROMOTION_THRESHOLD

        if not passed:
            failures.append(
                f"Average score {avg_score:.2f} is below threshold "
                f"{_PROMOTION_THRESHOLD:.2f}."
            )

        return EvaluationResult(passed=passed, scores=scores, failures=failures)

    async def promote_prompt(self, prompt_template_id: str) -> bool:
        """Promote a prompt to *active* only if its evaluation passes.

        Returns ``True`` if promotion succeeded, ``False`` otherwise.
        """
        evaluation = await self.evaluate_prompt(prompt_template_id)
        if not evaluation.passed:
            logger.warning(
                "Prompt %s failed evaluation — not promoted. Failures: %s",
                prompt_template_id,
                evaluation.failures,
            )
            return False

        template_uuid = UUID(prompt_template_id)

        # Fetch the template to determine its task_type + model_family so we
        # can deactivate any previously active prompt in the same slot.
        stmt = sa.select(PromptTemplate).where(PromptTemplate.id == template_uuid)
        result = await self._session.execute(stmt)
        template = result.scalar_one_or_none()
        if template is None:
            logger.error("Prompt template %s not found.", prompt_template_id)
            return False

        # Deactivate other active prompts for the same task/model slot.
        deactivate_stmt = (
            sa.update(PromptTemplate)
            .where(
                PromptTemplate.task_type == template.task_type,
                PromptTemplate.model_family == template.model_family,
                PromptTemplate.is_active.is_(True),
                PromptTemplate.id != template_uuid,
            )
            .values(is_active=False)
        )
        await self._session.execute(deactivate_stmt)

        # Activate the promoted prompt.
        template.is_active = True
        await self._session.flush()

        logger.info(
            "Promoted prompt %s v%d (id=%s) to active.",
            template.name,
            template.version,
            template.id,
        )
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _next_version(self, name: str) -> int:
        """Return the next version number for a prompt *name*."""
        stmt = (
            sa.select(sa.func.max(PromptTemplate.version))
            .where(PromptTemplate.name == name)
        )
        result = await self._session.execute(stmt)
        current_max = result.scalar_one_or_none()
        return (current_max or 0) + 1

    @staticmethod
    def _row_to_dict(row: PromptTemplate) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "name": row.name,
            "version": row.version,
            "task_type": row.task_type,
            "model_family": row.model_family,
            "system_prompt": row.system_prompt,
            "user_template": row.user_template,
            "input_schema": row.input_schema,
            "output_schema": row.output_schema,
            "evaluation_set_reference": row.evaluation_set_reference,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

"""Model Router — selects the appropriate model for a given task and tenant.

Currently implements simple default-model routing.  The design is intentionally
extensible for future tenant-specific overrides, cost-aware routing, and
fallback chains.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from packages.common.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Resolved model configuration for an inference call."""

    provider: str
    model_name: str
    max_tokens: int
    temperature: float


# Default temperature and max-output-tokens per task type.
_TASK_DEFAULTS: dict[str, dict[str, float | int]] = {
    "summarization": {"temperature": 0.3, "max_tokens": 2048},
    "question_answering": {"temperature": 0.2, "max_tokens": 4096},
    "classification": {"temperature": 0.0, "max_tokens": 256},
    "extraction": {"temperature": 0.0, "max_tokens": 4096},
    "analysis": {"temperature": 0.4, "max_tokens": 8192},
    "conversation": {"temperature": 0.7, "max_tokens": 4096},
}

_FALLBACK_DEFAULTS: dict[str, float | int] = {
    "temperature": 0.3,
    "max_tokens": 4096,
}


class ModelRouter:
    """Routes inference requests to an appropriate model.

    Parameters
    ----------
    default_provider:
        Override the provider from settings (e.g. ``"anthropic"``).
    default_model:
        Override the model name from settings (e.g. ``"claude-sonnet-4-20250514"``).
    """

    def __init__(
        self,
        default_provider: str | None = None,
        default_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._default_provider = default_provider or settings.DEFAULT_MODEL_PROVIDER
        self._default_model = default_model or settings.DEFAULT_MODEL_NAME

    async def route(
        self,
        task_type: str,
        tenant_id: UUID,
        context: dict | None = None,
    ) -> ModelConfig:
        """Determine the model to use for a given *task_type* and *tenant_id*.

        The current implementation returns the default model with
        task-appropriate temperature and max_tokens.  Future iterations will
        consult tenant settings and cost policies.

        Parameters
        ----------
        task_type:
            The kind of AI task (e.g. ``"summarization"``, ``"classification"``).
        tenant_id:
            The tenant making the request (reserved for per-tenant routing).
        context:
            Optional extra context (e.g. urgency, document size) that may
            influence routing decisions in the future.
        """
        ctx = context or {}
        task_cfg = _TASK_DEFAULTS.get(task_type, _FALLBACK_DEFAULTS)

        # TODO: Look up tenant-specific model overrides from the database.
        # e.g. some enterprise tenants may have access to larger models.

        provider = ctx.get("provider_override", self._default_provider)
        model = ctx.get("model_override", self._default_model)

        config = ModelConfig(
            provider=provider,
            model_name=model,
            max_tokens=int(ctx.get("max_tokens_override", task_cfg["max_tokens"])),
            temperature=float(ctx.get("temperature_override", task_cfg["temperature"])),
        )

        logger.debug(
            "Routed task_type=%s tenant=%s -> %s/%s (temp=%.1f, max_tokens=%d)",
            task_type,
            tenant_id,
            config.provider,
            config.model_name,
            config.temperature,
            config.max_tokens,
        )
        return config

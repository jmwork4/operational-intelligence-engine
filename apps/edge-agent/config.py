"""Edge Agent configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EdgeConfig:
    """Configuration for the OIE Edge Intelligence Agent.

    Attributes
    ----------
    api_url:
        Base URL of the OIE cloud API (e.g. ``https://api.oie.example.com``).
    api_key:
        API key for authenticating with the cloud API.
    tenant_id:
        Tenant UUID this agent belongs to.
    sync_interval_seconds:
        How often (in seconds) the agent attempts to sync queued events
        to the cloud.  Default 30.
    max_queue_size:
        Maximum number of events to buffer locally before dropping the
        oldest.  Default 10 000.
    local_rules:
        Simple threshold rules to evaluate locally at the edge, even when
        offline.  Each rule is a dict with keys ``name``, ``field``,
        ``operator`` (``>``, ``<``, ``>=``, ``<=``, ``==``, ``!=``),
        ``threshold``, and ``severity``.
    offline_storage_path:
        File path for persisting the event queue across agent restarts.
        If ``None``, events are only held in memory.
    """

    api_url: str
    api_key: str
    tenant_id: str
    sync_interval_seconds: int = 30
    max_queue_size: int = 10_000
    local_rules: list[dict[str, Any]] = field(default_factory=list)
    offline_storage_path: str | None = None

"""Base classes for the OIE integrations framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WebhookConfig:
    """Configuration for an outbound or inbound webhook."""

    url: str
    secret: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    retry_count: int = 3


@dataclass
class IntegrationEvent:
    """Normalised representation of an event received from an external system."""

    source: str
    event_type: str
    payload: dict[str, Any]
    received_at: datetime
    raw_data: bytes | str | None = None


# ---------------------------------------------------------------------------
# Connector ABC
# ---------------------------------------------------------------------------

class ConnectorBase(ABC):
    """Abstract base class that every integration connector must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the connector."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this connector integrates with."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish a connection to the external system."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down the connection gracefully."""

    @abstractmethod
    async def send(self, payload: dict[str, Any]) -> None:
        """Push a payload to the external system."""

    @abstractmethod
    async def receive(self) -> list[dict[str, Any]]:
        """Pull pending messages / events from the external system."""

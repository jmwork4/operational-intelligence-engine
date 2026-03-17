"""OIE Edge Intelligence Agent — local event processing with cloud sync."""

from __future__ import annotations

import asyncio
import json
import logging
import operator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .config import EdgeConfig

logger = logging.getLogger(__name__)

# Operator lookup for local rule evaluation
_OPS: dict[str, Any] = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


class EdgeAgent:
    """Lightweight edge agent that ingests events locally and syncs to the cloud.

    Features
    --------
    - Local event queue with configurable max size for offline buffering.
    - Simple threshold-based rule evaluation at the edge.
    - Periodic batch upload to the OIE cloud API.
    - Automatic retry on connectivity failures.
    - Optional disk persistence for the event queue.

    Parameters
    ----------
    config:
        An :class:`EdgeConfig` instance with connection and behaviour settings.
    """

    def __init__(self, config: EdgeConfig) -> None:
        self.config = config
        self._queue: list[dict[str, Any]] = []
        self._running = False
        self._sync_task: asyncio.Task[None] | None = None
        self._client: httpx.AsyncClient | None = None

        # Restore persisted queue if available
        self._restore_queue()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def ingest_event(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Ingest an event into the local queue and evaluate local rules.

        Returns a list of locally-triggered alerts (may be empty).
        """
        # Stamp event
        event.setdefault("ingested_at", datetime.now(timezone.utc).isoformat())
        event.setdefault("tenant_id", self.config.tenant_id)

        # Add to queue (drop oldest if at capacity)
        if len(self._queue) >= self.config.max_queue_size:
            dropped = self._queue.pop(0)
            logger.warning("Queue full — dropped oldest event", extra={"event": dropped.get("event_type")})
        self._queue.append(event)

        # Persist queue
        self._persist_queue()

        # Evaluate local rules
        triggered = await self.evaluate_local_rules(event)
        if triggered:
            logger.info("Local rules triggered", extra={"count": len(triggered)})

        return triggered

    async def evaluate_local_rules(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate simple threshold rules against an event locally.

        Only supports simple field-level comparisons (``>``, ``<``,
        ``>=``, ``<=``, ``==``, ``!=``).
        """
        alerts: list[dict[str, Any]] = []

        payload = event.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                payload = {}

        for rule in self.config.local_rules:
            field_name = rule.get("field", "")
            op_str = rule.get("operator", "")
            threshold = rule.get("threshold")
            op_fn = _OPS.get(op_str)

            if op_fn is None:
                continue

            value = payload.get(field_name) or event.get(field_name)
            if value is None:
                continue

            try:
                if op_fn(float(value), float(threshold)):
                    alerts.append({
                        "rule_name": rule.get("name", "unnamed_rule"),
                        "severity": rule.get("severity", "medium"),
                        "field": field_name,
                        "value": value,
                        "threshold": threshold,
                        "operator": op_str,
                        "event_type": event.get("event_type"),
                        "entity_id": event.get("entity_id"),
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                        "source": "edge_agent",
                    })
            except (TypeError, ValueError):
                continue

        return alerts

    async def sync(self) -> None:
        """Batch upload queued events to the cloud API.

        If the API is unreachable, events remain in the queue and will
        be retried on the next sync cycle.
        """
        if not self._queue:
            return

        if not await self._is_connected():
            logger.warning("Cloud API unreachable — %d events queued", len(self._queue))
            return

        # Take a snapshot of the current queue
        batch = list(self._queue)
        batch_size = len(batch)

        try:
            client = self._get_client()
            response = await client.post(
                f"{self.config.api_url}/api/v1/events/batch",
                json={"events": batch},
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "X-Tenant-ID": self.config.tenant_id,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()

            # Success — remove synced events from queue
            self._queue = self._queue[batch_size:]
            self._persist_queue()

            logger.info("Synced %d events to cloud", batch_size)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Cloud API returned error — events retained in queue",
                extra={"status": exc.response.status_code, "queued": len(self._queue)},
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning(
                "Cloud sync failed — events retained in queue",
                extra={"error": str(exc), "queued": len(self._queue)},
            )

    async def start(self) -> None:
        """Start the background sync loop."""
        if self._running:
            return

        self._running = True
        logger.info(
            "Edge agent started",
            extra={
                "sync_interval": self.config.sync_interval_seconds,
                "local_rules": len(self.config.local_rules),
            },
        )
        self._sync_task = asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        """Flush remaining events and shut down gracefully."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Final sync attempt
        logger.info("Flushing %d remaining events before shutdown", len(self._queue))
        await self.sync()

        # Close HTTP client
        if self._client:
            await self._client.aclose()
            self._client = None

        # Persist any remaining events
        self._persist_queue()
        logger.info("Edge agent stopped")

    async def _is_connected(self) -> bool:
        """Check if the cloud API is reachable."""
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.config.api_url}/",
                timeout=5.0,
            )
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    async def _sync_loop(self) -> None:
        """Run the periodic sync loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.sync_interval_seconds)
                await self.sync()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in sync loop")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    def _persist_queue(self) -> None:
        """Persist the event queue to disk if configured."""
        if not self.config.offline_storage_path:
            return
        try:
            path = Path(self.config.offline_storage_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._queue, default=str))
        except Exception:
            logger.exception("Failed to persist event queue")

    def _restore_queue(self) -> None:
        """Restore the event queue from disk if available."""
        if not self.config.offline_storage_path:
            return
        path = Path(self.config.offline_storage_path)
        if not path.exists():
            return
        try:
            self._queue = json.loads(path.read_text())
            logger.info("Restored %d events from disk", len(self._queue))
        except Exception:
            logger.exception("Failed to restore event queue")
            self._queue = []

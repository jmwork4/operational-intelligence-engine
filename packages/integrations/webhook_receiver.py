"""Inbound webhook processing for the OIE integrations framework."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from packages.schemas import EventCreate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

@dataclass
class FieldMapping:
    """Maps a field from an external payload to an OIE EventCreate field.

    Parameters
    ----------
    source_field:
        Dot-separated path into the external JSON payload (e.g. ``"data.id"``).
    target_field:
        Name of the target field on ``EventCreate``.
    transform:
        Optional callable applied to the extracted value before assignment.
    """

    source_field: str
    target_field: str
    transform: Callable[[Any], Any] | None = None


# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------

async def validate_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 signature against the raw request body.

    The *signature* value may optionally be prefixed with ``sha256=``.
    """
    clean_sig = signature.removeprefix("sha256=")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, clean_sig)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_dotted(data: dict[str, Any], path: str) -> Any:
    """Walk a dotted path like ``'foo.bar.baz'`` into *data*."""
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


# ---------------------------------------------------------------------------
# Inbound webhook processor
# ---------------------------------------------------------------------------

class InboundWebhookProcessor:
    """Processes inbound webhook requests and maps them to OIE events."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        """
        Parameters
        ----------
        secrets:
            Mapping of ``source`` name to shared secret used for HMAC
            signature verification.  If a source is not present here its
            webhooks are accepted without verification.
        """
        self._secrets: dict[str, str] = secrets or {}

    # -- public API --------------------------------------------------------

    async def process_webhook(
        self,
        source: str,
        headers: dict[str, str],
        body: bytes,
        field_mapping: dict[str, FieldMapping],
    ) -> list[EventCreate]:
        """Validate, parse and map an inbound webhook to OIE events.

        Parameters
        ----------
        source:
            Identifier for the external system (e.g. ``"samsara"``,
            ``"project44"``).
        headers:
            HTTP request headers (used for signature verification).
        body:
            Raw request body bytes.
        field_mapping:
            Mapping of ``EventCreate`` field names to ``FieldMapping``
            descriptors that specify how to extract values from the parsed
            payload.

        Returns
        -------
        list[EventCreate]
            One or more mapped events ready for ingestion.
        """
        # 1. Verify signature if a secret is configured for this source
        secret = self._secrets.get(source)
        if secret:
            sig = headers.get("x-hub-signature-256") or headers.get("x-signature") or ""
            if not await validate_signature(body, sig, secret):
                raise ValueError(f"Invalid webhook signature for source '{source}'")

        # 2. Parse JSON body
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Webhook body is not valid JSON: {exc}") from exc

        # 3. Normalise to list (some providers send a single object)
        items: list[dict[str, Any]]
        if isinstance(payload, list):
            items = payload
        else:
            items = [payload]

        # 4. Apply field mapping and build EventCreate instances
        events: list[EventCreate] = []
        for item in items:
            mapped: dict[str, Any] = {}
            for target, fm in field_mapping.items():
                raw = _resolve_dotted(item, fm.source_field)
                if raw is not None and fm.transform is not None:
                    raw = fm.transform(raw)
                if raw is not None:
                    mapped[target] = raw

            # Ensure required defaults
            mapped.setdefault("source_system", source)
            mapped.setdefault("event_type", "custom")
            mapped.setdefault("entity_type", "shipment")
            mapped.setdefault("entity_id", "unknown")
            mapped.setdefault("payload", item)
            mapped.setdefault("occurred_at", datetime.now(timezone.utc).isoformat())

            events.append(EventCreate(**mapped))

        logger.info(
            "Processed inbound webhook",
            extra={"source": source, "event_count": len(events)},
        )
        return events

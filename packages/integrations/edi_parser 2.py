"""EDI document parser for common logistics transaction sets."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _split_segments(content: str) -> list[list[str]]:
    """Split raw EDI content into a list of segments.

    Each segment is itself a list of element values (split on ``*``).
    Segments are delimited by ``~``.
    """
    segments: list[list[str]] = []
    for raw_seg in content.replace("\n", "").replace("\r", "").split("~"):
        seg = raw_seg.strip()
        if seg:
            segments.append(seg.split("*"))
    return segments


def _find_segments(segments: list[list[str]], segment_id: str) -> list[list[str]]:
    """Return all segments whose identifier (element 0) matches *segment_id*."""
    return [s for s in segments if s and s[0] == segment_id]


def _safe_get(segment: list[str], index: int, default: str = "") -> str:
    """Safely retrieve an element from a segment list."""
    return segment[index] if index < len(segment) else default


class EDIParser:
    """Parses common EDI transaction sets used in logistics and maps them to
    OIE-compatible event dictionaries.
    """

    # -----------------------------------------------------------------
    # 204 — Motor Carrier Load Tender
    # -----------------------------------------------------------------

    def parse_204(self, content: str) -> list[dict[str, Any]]:
        """Parse an EDI 204 (Motor Carrier Load Tender) document.

        Returns a list of event dicts with fields compatible with
        ``EventCreate``.
        """
        segments = _split_segments(content)
        events: list[dict[str, Any]] = []

        # Extract header-level info from B2 segment
        b2_segs = _find_segments(segments, "B2")
        reference = ""
        scac = ""
        if b2_segs:
            b2 = b2_segs[0]
            scac = _safe_get(b2, 2)
            reference = _safe_get(b2, 4)

        # Stop-off details from S5 segments
        s5_segs = _find_segments(segments, "S5")
        for s5 in s5_segs:
            stop_number = _safe_get(s5, 1)
            stop_reason = _safe_get(s5, 2)  # CL=complete load, PL=partial, etc.
            weight = _safe_get(s5, 3)
            weight_unit = _safe_get(s5, 4)

            events.append(
                {
                    "event_type": "order_created",
                    "entity_type": "shipment",
                    "entity_id": reference or f"204-{stop_number}",
                    "source_system": "edi",
                    "payload": {
                        "edi_type": "204",
                        "scac": scac,
                        "reference": reference,
                        "stop_number": stop_number,
                        "stop_reason": stop_reason,
                        "weight": weight,
                        "weight_unit": weight_unit,
                    },
                }
            )

        # If no S5 segments, emit a single event from the header
        if not events:
            events.append(
                {
                    "event_type": "order_created",
                    "entity_type": "shipment",
                    "entity_id": reference or "unknown",
                    "source_system": "edi",
                    "payload": {
                        "edi_type": "204",
                        "scac": scac,
                        "reference": reference,
                    },
                }
            )

        logger.info("Parsed EDI 204", extra={"event_count": len(events)})
        return events

    # -----------------------------------------------------------------
    # 214 — Shipment Status Message
    # -----------------------------------------------------------------

    def parse_214(self, content: str) -> list[dict[str, Any]]:
        """Parse an EDI 214 (Transportation Carrier Shipment Status) document.

        The 214 is the most common status update in logistics EDI.
        """
        segments = _split_segments(content)
        events: list[dict[str, Any]] = []

        # B10 — shipment identification
        b10_segs = _find_segments(segments, "B10")
        shipment_id = ""
        scac = ""
        if b10_segs:
            b10 = b10_segs[0]
            shipment_id = _safe_get(b10, 1)
            scac = _safe_get(b10, 3)

        # AT7 — shipment status details
        at7_segs = _find_segments(segments, "AT7")
        for at7 in at7_segs:
            status_code = _safe_get(at7, 1)
            reason_code = _safe_get(at7, 2)
            date_str = _safe_get(at7, 5)
            time_str = _safe_get(at7, 6)

            occurred_at = None
            if date_str:
                try:
                    dt_str = date_str + time_str if time_str else date_str
                    fmt = "%Y%m%d%H%M" if time_str else "%Y%m%d"
                    occurred_at = datetime.strptime(dt_str, fmt).replace(
                        tzinfo=timezone.utc
                    ).isoformat()
                except ValueError:
                    pass

            event: dict[str, Any] = {
                "event_type": "shipment_dispatched",
                "entity_type": "shipment",
                "entity_id": shipment_id or "unknown",
                "source_system": "edi",
                "payload": {
                    "edi_type": "214",
                    "scac": scac,
                    "status_code": status_code,
                    "reason_code": reason_code,
                },
            }
            if occurred_at:
                event["occurred_at"] = occurred_at

            events.append(event)

        if not events:
            events.append(
                {
                    "event_type": "shipment_dispatched",
                    "entity_type": "shipment",
                    "entity_id": shipment_id or "unknown",
                    "source_system": "edi",
                    "payload": {"edi_type": "214", "scac": scac},
                }
            )

        logger.info("Parsed EDI 214", extra={"event_count": len(events)})
        return events

    # -----------------------------------------------------------------
    # 990 — Response to Load Tender
    # -----------------------------------------------------------------

    def parse_990(self, content: str) -> list[dict[str, Any]]:
        """Parse an EDI 990 (Response to Load Tender) document."""
        segments = _split_segments(content)
        events: list[dict[str, Any]] = []

        # B1 — beginning segment for the 990
        b1_segs = _find_segments(segments, "B1")
        scac = ""
        reference = ""
        response_code = ""
        if b1_segs:
            b1 = b1_segs[0]
            scac = _safe_get(b1, 1)
            reference = _safe_get(b1, 2)
            # Element 4 is typically the accept/decline code
            response_code = _safe_get(b1, 4)

        accepted = response_code.upper() == "A" if response_code else None

        events.append(
            {
                "event_type": "order_updated",
                "entity_type": "shipment",
                "entity_id": reference or "unknown",
                "source_system": "edi",
                "payload": {
                    "edi_type": "990",
                    "scac": scac,
                    "reference": reference,
                    "response_code": response_code,
                    "accepted": accepted,
                },
            }
        )

        logger.info("Parsed EDI 990", extra={"event_count": len(events)})
        return events

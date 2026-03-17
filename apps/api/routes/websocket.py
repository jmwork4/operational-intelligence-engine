"""WebSocket endpoint for real-time event streaming."""

from __future__ import annotations

import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter(tags=["WebSocket"])

# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

EVENT_TYPES = [
    "shipment_delayed",
    "temperature_reading",
    "driver_checkin",
    "route_deviated",
    "inventory_received",
    "delivery_completed",
    "vehicle_status_changed",
    "vendor_delay",
]

VENDORS = ["FastFreight", "ExpressLogistics", "SwiftShip", "CargoOne", "PrimeHaul"]
DRIVERS = ["M. Chen", "A. Rodriguez", "K. Patel", "T. Williams", "S. Nakamura"]
ROUTES = ["I-95 North", "US-20 West", "I-10 East", "SR-99 South", "I-75 North"]


def _random_event() -> dict[str, Any]:
    """Generate a random operational event."""
    etype = random.choice(EVENT_TYPES)
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "event_id": f"EVT-{uuid4().hex[:8].upper()}",
        "event_type": etype,
        "timestamp": now,
        "vendor": random.choice(VENDORS),
    }
    if etype == "shipment_delayed":
        base["delay_minutes"] = random.randint(5, 120)
        base["priority"] = random.choice(["low", "medium", "high"])
    elif etype == "temperature_reading":
        base["temperature_f"] = round(random.uniform(32, 110), 1)
        base["sensor_id"] = f"SENS-{random.randint(100, 999)}"
    elif etype == "driver_checkin":
        base["driver"] = random.choice(DRIVERS)
        base["location"] = random.choice(ROUTES)
    elif etype == "route_deviated":
        base["deviation_km"] = round(random.uniform(0.5, 15.0), 1)
        base["driver"] = random.choice(DRIVERS)
    elif etype == "delivery_completed":
        base["on_time"] = random.choice([True, True, True, False])
        base["driver"] = random.choice(DRIVERS)
    return base


ALERT_TITLES = [
    "Late Shipment Alert",
    "Temperature Excursion",
    "Route Deviation Detected",
    "Driver Idle Warning",
    "Vendor Delay Pattern",
    "Delivery SLA Breach",
]


def _random_alert() -> dict[str, Any]:
    """Generate a random alert notification."""
    severity = random.choices(
        ["low", "medium", "high", "critical"], weights=[1, 3, 4, 2]
    )[0]
    return {
        "alert_id": f"ALR-{uuid4().hex[:8].upper()}",
        "title": random.choice(ALERT_TITLES),
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule_id": f"RUL-{random.randint(1, 8):03d}",
        "message": "Automatically triggered by rule engine.",
    }


def _kpi_snapshot() -> dict[str, Any]:
    """Generate a KPI update snapshot."""
    return {
        "events_today": random.randint(12000, 14000),
        "active_rules": 156,
        "open_alerts": random.randint(30, 50),
        "ai_queries": random.randint(250, 320),
        "avg_response_sec": round(random.uniform(2.0, 5.0), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# WebSocket route
# ---------------------------------------------------------------------------

@router.websocket("/ws/events/{tenant_id}")
async def websocket_events(
    websocket: WebSocket,
    tenant_id: str,
    token: str = Query(default=""),
):
    """Stream real-time events, alerts, and KPI updates to a connected client.

    Query Parameters
    ----------------
    token : str
        Authentication token (validated on connect).
    """
    # Simple token validation (in production, verify JWT)
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    await websocket.accept()

    # Counters for periodic messages
    last_kpi_time = time.monotonic()

    try:
        while True:
            # Random event every 2-5 seconds
            delay = random.uniform(2.0, 5.0)
            await asyncio.sleep(delay)

            # Send event
            event = _random_event()
            await websocket.send_json({"type": "event", "data": event})

            # Occasionally send an alert (roughly 1 in 3 cycles)
            if random.random() < 0.33:
                alert = _random_alert()
                await websocket.send_json({"type": "alert", "data": alert})

            # KPI update every ~10 seconds
            now = time.monotonic()
            if now - last_kpi_time >= 10.0:
                kpi = _kpi_snapshot()
                await websocket.send_json({"type": "kpi_update", "data": kpi})
                last_kpi_time = now

    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=1011, reason="Internal error")

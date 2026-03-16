from enum import StrEnum
from typing import NewType
from uuid import UUID

TenantId = NewType("TenantId", UUID)
UserId = NewType("UserId", UUID)


class EntityType(StrEnum):
    SHIPMENT = "shipment"
    VEHICLE = "vehicle"
    DRIVER = "driver"
    WAREHOUSE = "warehouse"
    INVENTORY = "inventory"
    VENDOR = "vendor"
    ROUTE = "route"
    ORDER = "order"


class EventType(StrEnum):
    SHIPMENT_DISPATCHED = "shipment_dispatched"
    SHIPMENT_DELAYED = "shipment_delayed"
    DELIVERY_COMPLETED = "delivery_completed"
    DRIVER_CHECKIN = "driver_checkin"
    INVENTORY_RECEIVED = "inventory_received"
    VEHICLE_STATUS_CHANGED = "vehicle_status_changed"
    ROUTE_DEVIATED = "route_deviated"
    VENDOR_DELAY = "vendor_delay"
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    CUSTOM = "custom"


class RuleType(StrEnum):
    EVENT_TRIGGERED = "event_triggered"
    THRESHOLD = "threshold"
    COMPOSITE = "composite"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(StrEnum):
    ALERT = "alert"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    WORKFLOW = "workflow"


class AlertStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

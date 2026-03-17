"""Logistics industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

LOGISTICS = VerticalPackage(
    name="logistics",
    display_name="Logistics & Transportation",
    description=(
        "End-to-end logistics operations monitoring — shipment tracking, "
        "fleet management, vendor performance, and delivery SLA compliance."
    ),
    event_types=[
        {
            "name": "shipment_dispatched",
            "description": "A shipment has been dispatched from origin",
            "fields": ["shipment_id", "origin", "destination", "carrier_id", "eta"],
        },
        {
            "name": "shipment_delayed",
            "description": "A shipment has been delayed beyond its scheduled time",
            "fields": ["shipment_id", "delay_minutes", "reason", "new_eta"],
        },
        {
            "name": "delivery_completed",
            "description": "A delivery has been successfully completed",
            "fields": ["shipment_id", "delivered_at", "recipient", "condition"],
        },
        {
            "name": "driver_checkin",
            "description": "Driver check-in at a waypoint or facility",
            "fields": ["driver_id", "location", "vehicle_id", "status"],
        },
        {
            "name": "inventory_received",
            "description": "Inventory has been received at a warehouse or facility",
            "fields": ["warehouse_id", "sku", "quantity", "supplier_id", "po_number"],
        },
        {
            "name": "vehicle_status_changed",
            "description": "A vehicle's operational status has changed",
            "fields": ["vehicle_id", "old_status", "new_status", "mileage", "location"],
        },
        {
            "name": "route_deviated",
            "description": "A vehicle has deviated from its planned route",
            "fields": ["vehicle_id", "driver_id", "deviation_km", "reason"],
        },
        {
            "name": "vendor_delay",
            "description": "A vendor has caused a delay in the supply chain",
            "fields": ["vendor_id", "delay_minutes", "affected_shipments", "reason"],
        },
        {
            "name": "dock_appointment",
            "description": "A dock appointment has been scheduled or updated",
            "fields": ["dock_id", "warehouse_id", "carrier_id", "scheduled_at", "status"],
        },
        {
            "name": "load_tender",
            "description": "A load tender has been submitted or accepted",
            "fields": ["tender_id", "carrier_id", "origin", "destination", "rate", "status"],
        },
        {
            "name": "proof_of_delivery",
            "description": "Proof of delivery has been captured",
            "fields": ["shipment_id", "signed_by", "photo_url", "timestamp", "notes"],
        },
        {
            "name": "carrier_assigned",
            "description": "A carrier has been assigned to a shipment",
            "fields": ["shipment_id", "carrier_id", "rate", "pickup_date", "delivery_date"],
        },
    ],
    rule_templates=[
        {
            "name": "Late Shipment Alert",
            "type": "threshold",
            "expression": "event.delay_minutes > 30",
            "severity": "high",
            "description": "Alert when a shipment is delayed more than 30 minutes",
        },
        {
            "name": "Critical Shipment Delay",
            "type": "threshold",
            "expression": "event.delay_minutes > 120",
            "severity": "critical",
            "description": "Critical alert for shipments delayed over 2 hours",
        },
        {
            "name": "Route Deviation Alert",
            "type": "threshold",
            "expression": "event.deviation_km > 5",
            "severity": "medium",
            "description": "Alert when a vehicle deviates more than 5km from planned route",
        },
        {
            "name": "Vendor Reliability Warning",
            "type": "frequency",
            "expression": "count(vendor_delay) > 3 within 7d per vendor_id",
            "severity": "high",
            "description": "Alert when a vendor causes more than 3 delays in a week",
        },
        {
            "name": "Driver Idle Time",
            "type": "absence",
            "expression": "no driver_checkin for 4h per driver_id",
            "severity": "medium",
            "description": "Alert when a driver has not checked in for 4 hours",
        },
        {
            "name": "Delivery SLA Breach",
            "type": "threshold",
            "expression": "delivery_time > sla_target",
            "severity": "high",
            "description": "Alert when a delivery exceeds the agreed SLA window",
        },
        {
            "name": "Fleet Maintenance Due",
            "type": "threshold",
            "expression": "event.mileage > maintenance_threshold",
            "severity": "low",
            "description": "Notify when a vehicle is approaching maintenance mileage",
        },
        {
            "name": "Dock Congestion",
            "type": "frequency",
            "expression": "count(dock_appointment{status='waiting'}) > 5 within 1h per warehouse_id",
            "severity": "medium",
            "description": "Alert when dock congestion exceeds threshold",
        },
        {
            "name": "Load Tender Rejection Rate",
            "type": "frequency",
            "expression": "count(load_tender{status='rejected'}) > 3 within 24h per carrier_id",
            "severity": "high",
            "description": "Alert when a carrier rejects too many load tenders",
        },
        {
            "name": "Multi-Vendor Failure Correlation",
            "type": "correlation",
            "expression": "vendor_delay AND shipment_delayed within 2h same shipment_id",
            "severity": "critical",
            "description": "Correlate vendor delays with downstream shipment delays",
        },
    ],
    prompt_templates=[
        {
            "name": "logistics_query",
            "task_type": "query",
            "system_prompt": (
                "You are an operations intelligence assistant specialising in logistics "
                "and transportation. Answer questions about shipments, deliveries, fleet "
                "status, and vendor performance using the provided operational data. "
                "Be concise, cite specific shipment IDs and metrics."
            ),
        },
        {
            "name": "shipment_analysis",
            "task_type": "analysis",
            "system_prompt": (
                "Analyse the following shipment data and identify patterns, risks, and "
                "optimisation opportunities. Focus on delay patterns, carrier performance, "
                "route efficiency, and SLA compliance. Provide actionable recommendations."
            ),
        },
        {
            "name": "vendor_evaluation",
            "task_type": "analysis",
            "system_prompt": (
                "Evaluate vendor performance based on the provided delivery data. "
                "Assess reliability, delay frequency, cost efficiency, and overall "
                "supply chain impact. Recommend actions for underperforming vendors."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "On-Time Delivery Rate", "metric": "on_time_rate", "format": "percent", "target": 95},
            {"label": "Active Shipments", "metric": "active_shipments", "format": "number"},
            {"label": "Avg Delay (min)", "metric": "avg_delay_minutes", "format": "number", "target": 15},
            {"label": "Fleet Utilisation", "metric": "fleet_utilisation", "format": "percent", "target": 85},
        ],
        "chart_types": [
            {"type": "line", "title": "Delivery Performance Trend", "metric": "on_time_rate", "period": "30d"},
            {"type": "bar", "title": "Delays by Carrier", "metric": "delay_count", "group_by": "carrier_id"},
            {"type": "pie", "title": "Shipments by Status", "metric": "shipment_count", "group_by": "status"},
            {"type": "heatmap", "title": "Delivery Heatmap", "metric": "delivery_count", "group_by": "region"},
        ],
    },
    document_templates=[
        "Standard Operating Procedures (SOP)",
        "Carrier Rate Agreements",
        "SLA Definitions",
        "Route Planning Guidelines",
        "Incident Response Procedures",
        "Vendor Onboarding Checklist",
    ],
)

register_vertical(LOGISTICS)

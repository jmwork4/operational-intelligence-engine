"""Merchandise Supply Chain industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

MERCHANDISE_SUPPLY_CHAIN = VerticalPackage(
    name="merchandise_supply_chain",
    display_name="Merchandise Supply Chain",
    description=(
        "Global merchandise supply chain operations — container tracking, customs clearance, "
        "vendor management, DC operations, inventory allocation, and demand planning."
    ),
    event_types=[
        {
            "name": "container_departed",
            "description": "A container has departed from the origin port or facility",
            "fields": ["container_id", "origin_port", "destination_port", "vessel_id", "eta"],
        },
        {
            "name": "container_arrived",
            "description": "A container has arrived at the destination port or facility",
            "fields": ["container_id", "port", "arrived_at", "vessel_id", "status"],
        },
        {
            "name": "port_dwell_started",
            "description": "A container has begun dwelling at a port awaiting pickup",
            "fields": ["container_id", "port", "dwell_start", "reason", "expected_pickup"],
        },
        {
            "name": "customs_cleared",
            "description": "A shipment has cleared customs inspection",
            "fields": ["container_id", "customs_id", "cleared_at", "duty_amount", "broker_id"],
        },
        {
            "name": "customs_hold",
            "description": "A shipment has been placed on customs hold",
            "fields": ["container_id", "customs_id", "hold_reason", "hold_start", "resolution_eta"],
        },
        {
            "name": "transshipment_completed",
            "description": "A container has been transshipped to a new vessel or mode",
            "fields": ["container_id", "from_vessel", "to_vessel", "port", "completed_at"],
        },
        {
            "name": "vendor_shipment_dispatched",
            "description": "A vendor has dispatched a shipment",
            "fields": ["vendor_id", "po_number", "ship_date", "container_id", "quantity"],
        },
        {
            "name": "vendor_shipment_delayed",
            "description": "A vendor shipment has been delayed past the ship window",
            "fields": ["vendor_id", "po_number", "original_ship_date", "new_ship_date", "reason"],
        },
        {
            "name": "dc_received",
            "description": "Merchandise has been received at a distribution centre",
            "fields": ["dc_id", "container_id", "po_number", "quantity", "received_at"],
        },
        {
            "name": "quality_inspection",
            "description": "A quality inspection has been performed on received merchandise",
            "fields": ["inspection_id", "dc_id", "po_number", "pass_rate", "defects"],
        },
        {
            "name": "inventory_allocated",
            "description": "Inventory has been allocated to stores or channels",
            "fields": ["sku", "dc_id", "allocated_qty", "total_available", "allocated_pct"],
        },
        {
            "name": "store_delivery",
            "description": "Merchandise has been delivered to a retail store",
            "fields": ["store_id", "dc_id", "shipment_id", "delivered_at", "quantity"],
        },
        {
            "name": "stock_transfer",
            "description": "Inventory has been transferred between locations",
            "fields": ["from_location", "to_location", "sku", "quantity", "transfer_id"],
        },
        {
            "name": "demand_forecast_updated",
            "description": "A demand forecast has been updated for a product or category",
            "fields": ["sku", "category", "forecast_qty", "period", "confidence"],
        },
        {
            "name": "purchase_order_created",
            "description": "A new purchase order has been created for a vendor",
            "fields": ["po_number", "vendor_id", "sku_count", "total_units", "ship_by_date"],
        },
    ],
    rule_templates=[
        {
            "name": "Port Dwell Time Exceeded",
            "type": "threshold",
            "expression": "event.dwell_hours > 48 per container_id",
            "severity": "high",
            "description": "Alert when a container has dwelled at port for more than 48 hours",
        },
        {
            "name": "Customs Hold Detected",
            "type": "event",
            "expression": "on customs_hold",
            "severity": "high",
            "description": "Alert immediately when a shipment is placed on customs hold",
        },
        {
            "name": "Vendor Missed Ship Window",
            "type": "event",
            "expression": "on vendor_shipment_delayed",
            "severity": "medium",
            "description": "Alert when a vendor misses their committed ship window",
        },
        {
            "name": "Vendor Reliability Declining",
            "type": "frequency",
            "expression": "count(vendor_shipment_delayed) > 3 within 30d per vendor_id",
            "severity": "high",
            "description": "Alert when a vendor has more than 3 delays in 30 days",
        },
        {
            "name": "Container Tracking Lost",
            "type": "absence",
            "expression": "no container_arrived AND no container_departed for 72h per container_id",
            "severity": "critical",
            "description": "Critical alert when no tracking update received for a container in 72 hours",
        },
        {
            "name": "DC Receiving Delay",
            "type": "threshold",
            "expression": "event.hours_past_expected > 24 per container_id",
            "severity": "medium",
            "description": "Alert when DC receiving is more than 24 hours past expected time",
        },
        {
            "name": "QC Inspection Failed",
            "type": "event",
            "expression": "on quality_inspection where pass_rate < 90",
            "severity": "high",
            "description": "Alert when a quality inspection fails at the distribution centre",
        },
        {
            "name": "Inventory Allocation Below Forecast",
            "type": "threshold",
            "expression": "event.allocated_pct < 80 per sku",
            "severity": "high",
            "description": "Alert when inventory allocation is below 80% of forecast demand",
        },
        {
            "name": "Seasonal Deadline at Risk",
            "type": "correlation",
            "expression": "days_to_launch < 21 AND allocated_pct < 90 per sku",
            "severity": "critical",
            "description": "Critical alert when seasonal launch is within 21 days and allocation is below 90%",
        },
        {
            "name": "Store Stockout Risk",
            "type": "threshold",
            "expression": "event.on_hand_days < 7 per store_id per sku",
            "severity": "high",
            "description": "Alert when store on-hand inventory falls below 7 days of supply",
        },
        {
            "name": "Transit Time Exceeding Average",
            "type": "threshold",
            "expression": "event.transit_days > avg_transit_days * 1.5 per lane",
            "severity": "medium",
            "description": "Alert when transit time exceeds 1.5x the average for a trade lane",
        },
        {
            "name": "Purchase Order Overdue",
            "type": "threshold",
            "expression": "event.days_past_due > 7 per po_number",
            "severity": "medium",
            "description": "Alert when a purchase order is more than 7 days past its due date",
        },
    ],
    prompt_templates=[
        {
            "name": "supply_chain_query",
            "task_type": "query",
            "system_prompt": (
                "You are a global merchandise supply chain assistant. Answer questions "
                "about container tracking, vendor performance, inventory allocation, and "
                "transit times using the provided operational data. Reference specific "
                "container IDs, PO numbers, and vendor metrics."
            ),
        },
        {
            "name": "vendor_evaluation",
            "task_type": "analysis",
            "system_prompt": (
                "You are a vendor performance analyst. Evaluate supplier reliability, "
                "quality scores, lead times, and compliance with ship windows. Identify "
                "trends in vendor performance and recommend actions for underperforming "
                "suppliers including corrective action plans or sourcing alternatives."
            ),
        },
        {
            "name": "demand_planning",
            "task_type": "analysis",
            "system_prompt": (
                "You are a demand planning assistant. Analyse inventory levels against "
                "forecasts, identify stockout risks, and recommend allocation adjustments. "
                "Consider seasonal patterns, lead times, and current pipeline inventory "
                "to provide actionable replenishment and allocation recommendations."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "Containers in Transit", "metric": "containers_in_transit", "format": "number"},
            {"label": "Vendor On-Time %", "metric": "vendor_on_time_rate", "format": "percent", "target": 90},
            {"label": "Allocation Completion", "metric": "allocation_completion", "format": "percent", "target": 95},
            {"label": "Stockout Risk Count", "metric": "stockout_risk_count", "format": "number", "target": 0},
        ],
        "chart_types": [
            {"type": "line", "title": "Vendor On-Time Trend", "metric": "vendor_on_time_rate", "period": "30d"},
            {"type": "bar", "title": "Port Dwell Time by Port", "metric": "avg_dwell_hours", "group_by": "port"},
            {"type": "pie", "title": "Containers by Status", "metric": "container_count", "group_by": "status"},
            {"type": "heatmap", "title": "Transit Time by Lane", "metric": "avg_transit_days", "group_by": "lane"},
        ],
    },
    document_templates=[
        "Vendor Compliance Manual",
        "Import/Export Procedures",
        "Quality Assurance Standards",
        "Allocation Planning Guidelines",
        "Customs Brokerage Agreements",
        "Distribution Centre SOP",
    ],
)

register_vertical(MERCHANDISE_SUPPLY_CHAIN)

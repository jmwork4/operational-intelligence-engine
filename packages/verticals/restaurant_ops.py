"""Restaurant Operations industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

RESTAURANT_OPS = VerticalPackage(
    name="restaurant_ops",
    display_name="Restaurant Operations",
    description=(
        "Multi-location restaurant operations — food safety, equipment monitoring, "
        "drive-thru performance, labor management, and health inspection compliance."
    ),
    event_types=[
        {
            "name": "cooler_temperature",
            "description": "A temperature reading from a walk-in cooler",
            "fields": ["sensor_id", "location_id", "temperature_f", "unit_name", "timestamp"],
        },
        {
            "name": "freezer_temperature",
            "description": "A temperature reading from a walk-in freezer",
            "fields": ["sensor_id", "location_id", "temperature_f", "unit_name", "timestamp"],
        },
        {
            "name": "fryer_oil_reading",
            "description": "A total polar materials (TPM) reading from a fryer",
            "fields": ["fryer_id", "location_id", "tpm_pct", "last_changed", "timestamp"],
        },
        {
            "name": "supplier_delivery",
            "description": "A supplier delivery has arrived or is expected at a location",
            "fields": ["supplier_id", "location_id", "scheduled_at", "arrived_at", "status"],
        },
        {
            "name": "food_waste_logged",
            "description": "Food waste has been logged at a location",
            "fields": ["location_id", "product", "quantity_lbs", "reason", "logged_by"],
        },
        {
            "name": "inventory_count",
            "description": "An inventory count has been performed at a location",
            "fields": ["location_id", "product", "counted_qty", "expected_qty", "variance_pct"],
        },
        {
            "name": "health_inspection",
            "description": "A health department inspection has been completed",
            "fields": ["location_id", "inspector", "score", "violations", "inspection_date"],
        },
        {
            "name": "sanitation_completed",
            "description": "A sanitation task has been completed at a location",
            "fields": ["location_id", "zone", "completed_by", "completed_at", "verified"],
        },
        {
            "name": "equipment_alert",
            "description": "An equipment issue has been detected at a location",
            "fields": ["location_id", "equipment_id", "equipment_type", "alert_type", "severity"],
        },
        {
            "name": "drive_thru_time",
            "description": "A drive-thru service time measurement",
            "fields": ["location_id", "order_id", "elapsed_seconds", "window", "timestamp"],
        },
        {
            "name": "order_fulfillment_time",
            "description": "An order fulfillment time measurement",
            "fields": ["location_id", "order_id", "elapsed_seconds", "channel", "timestamp"],
        },
        {
            "name": "customer_complaint",
            "description": "A customer complaint has been logged",
            "fields": ["location_id", "complaint_type", "channel", "severity", "details"],
        },
        {
            "name": "pos_sales_update",
            "description": "A point-of-sale sales data update",
            "fields": ["location_id", "period", "net_sales", "transaction_count", "avg_ticket"],
        },
        {
            "name": "labor_clock_event",
            "description": "An employee clock-in or clock-out event",
            "fields": ["location_id", "employee_id", "event_type", "role", "timestamp"],
        },
        {
            "name": "shift_started",
            "description": "A shift has started at a location",
            "fields": ["location_id", "shift_id", "manager_id", "headcount", "started_at"],
        },
    ],
    rule_templates=[
        {
            "name": "Walk-in Cooler Excursion",
            "type": "threshold",
            "expression": "event.temperature_f > 41 for 10m per location_id per unit_name",
            "severity": "critical",
            "description": "Critical alert when walk-in cooler temperature exceeds 41°F for 10 minutes",
        },
        {
            "name": "Freezer Excursion",
            "type": "threshold",
            "expression": "event.temperature_f > 0 for 10m per location_id per unit_name",
            "severity": "critical",
            "description": "Critical alert when freezer temperature exceeds 0°F for 10 minutes",
        },
        {
            "name": "Fryer Oil Degraded",
            "type": "threshold",
            "expression": "event.tpm_pct > 24 per fryer_id",
            "severity": "medium",
            "description": "Alert when fryer oil TPM exceeds 24% indicating oil change needed",
        },
        {
            "name": "Supplier Delivery Late",
            "type": "threshold",
            "expression": "event.delay_minutes > 120 per supplier_id per location_id",
            "severity": "high",
            "description": "Alert when a supplier delivery is more than 2 hours late",
        },
        {
            "name": "Food Waste Spike",
            "type": "threshold",
            "expression": "event.waste_quantity > 2 * avg_waste for 3d per location_id",
            "severity": "medium",
            "description": "Alert when food waste exceeds 2x normal levels for 3 consecutive days",
        },
        {
            "name": "Health Inspection Below Threshold",
            "type": "threshold",
            "expression": "event.score < 90 per location_id",
            "severity": "critical",
            "description": "Critical alert when a health inspection score falls below 90",
        },
        {
            "name": "Equipment Failure Detected",
            "type": "event",
            "expression": "on equipment_alert where alert_type == 'failure'",
            "severity": "high",
            "description": "Alert immediately when an equipment failure is detected",
        },
        {
            "name": "Drive-Thru Time Exceeded",
            "type": "threshold",
            "expression": "avg(event.elapsed_seconds) > 240 for 30m per location_id",
            "severity": "medium",
            "description": "Alert when average drive-thru time exceeds 240 seconds for 30 minutes",
        },
        {
            "name": "Sanitation Overdue",
            "type": "absence",
            "expression": "no sanitation_completed for 4h per location_id per zone",
            "severity": "high",
            "description": "Alert when sanitation has not been completed within 4 hours for a zone",
        },
        {
            "name": "Sales/Labor Ratio Low",
            "type": "threshold",
            "expression": "event.sales_labor_ratio < target_ratio for 2h per location_id",
            "severity": "medium",
            "description": "Alert when sales-to-labor ratio falls below target for 2 hours",
        },
        {
            "name": "Customer Complaint Spike",
            "type": "frequency",
            "expression": "count(customer_complaint) >= 3 within 1h per location_id",
            "severity": "high",
            "description": "Alert when 3 or more customer complaints are received within 1 hour",
        },
        {
            "name": "Inventory Discrepancy",
            "type": "threshold",
            "expression": "event.variance_pct > 10 per location_id per product",
            "severity": "medium",
            "description": "Alert when inventory count variance exceeds 10% from expected",
        },
    ],
    prompt_templates=[
        {
            "name": "restaurant_ops_query",
            "task_type": "query",
            "system_prompt": (
                "You are a restaurant operations assistant. Answer questions about food "
                "safety compliance, equipment status, labor efficiency, and service "
                "performance across all locations using the provided operational data. "
                "Reference specific location IDs, timestamps, and metrics."
            ),
        },
        {
            "name": "location_analysis",
            "task_type": "analysis",
            "system_prompt": (
                "You are a multi-location restaurant analyst. Compare store performance, "
                "identify underperforming locations, and analyse trends in food costs, "
                "labor, and customer satisfaction. Provide benchmarking insights and "
                "actionable recommendations for each location."
            ),
        },
        {
            "name": "health_compliance",
            "task_type": "analysis",
            "system_prompt": (
                "You are a health and safety compliance assistant. Assess inspection "
                "readiness, identify compliance gaps, and recommend corrective actions "
                "for restaurant operations. Reference health code requirements, past "
                "inspection history, and current operational data."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "Locations Compliant", "metric": "locations_compliant", "format": "percent", "target": 100},
            {"label": "Avg Drive-Thru Time", "metric": "avg_drive_thru_seconds", "format": "number", "target": 180},
            {"label": "Food Cost %", "metric": "food_cost_pct", "format": "percent", "target": 30},
            {"label": "Equipment Uptime %", "metric": "equipment_uptime", "format": "percent", "target": 98},
        ],
        "chart_types": [
            {"type": "line", "title": "Drive-Thru Performance Trend", "metric": "avg_drive_thru_seconds", "period": "30d"},
            {"type": "bar", "title": "Compliance Score by Location", "metric": "health_score", "group_by": "location_id"},
            {"type": "pie", "title": "Complaints by Type", "metric": "complaint_count", "group_by": "complaint_type"},
            {"type": "heatmap", "title": "Sales by Location & Hour", "metric": "net_sales", "group_by": "location_id"},
        ],
    },
    document_templates=[
        "Health Inspection Checklist",
        "Food Safety Operating Procedures",
        "Equipment Maintenance Schedule",
        "Employee Training Manual",
        "Waste Reduction Guidelines",
        "Drive-Thru Service Standards",
    ],
)

register_vertical(RESTAURANT_OPS)

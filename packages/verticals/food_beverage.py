"""Food & Beverage industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

FOOD_BEVERAGE = VerticalPackage(
    name="food_beverage",
    display_name="Food & Beverage",
    description=(
        "Food safety and quality operations — temperature monitoring, FSMA compliance, "
        "supplier quality, shelf life management, and waste tracking."
    ),
    event_types=[
        {
            "name": "temperature_reading",
            "description": "A temperature sensor reading from a cold storage unit",
            "fields": ["sensor_id", "zone", "temperature_f", "unit_id", "timestamp"],
        },
        {
            "name": "humidity_reading",
            "description": "A humidity sensor reading from a storage or production area",
            "fields": ["sensor_id", "zone", "humidity_pct", "timestamp"],
        },
        {
            "name": "cooler_excursion",
            "description": "A cooler has exceeded its safe temperature range",
            "fields": ["unit_id", "zone", "temperature_f", "duration_minutes", "threshold_f"],
        },
        {
            "name": "freezer_excursion",
            "description": "A freezer has exceeded its safe temperature range",
            "fields": ["unit_id", "zone", "temperature_f", "duration_minutes", "threshold_f"],
        },
        {
            "name": "supplier_delivery",
            "description": "A supplier delivery has arrived or is expected",
            "fields": ["supplier_id", "po_number", "scheduled_at", "arrived_at", "status"],
        },
        {
            "name": "quality_inspection",
            "description": "A quality inspection has been completed on incoming goods",
            "fields": ["inspection_id", "supplier_id", "score", "defects", "inspector_id"],
        },
        {
            "name": "product_received",
            "description": "Product has been received and logged into inventory",
            "fields": ["product_id", "batch_id", "quantity", "supplier_id", "expiry_date"],
        },
        {
            "name": "shelf_life_check",
            "description": "A shelf life check has been performed on stored product",
            "fields": ["product_id", "batch_id", "days_remaining", "zone", "action_required"],
        },
        {
            "name": "batch_released",
            "description": "A product batch has been released for distribution",
            "fields": ["batch_id", "product_id", "quantity", "released_by", "destination"],
        },
        {
            "name": "contamination_alert",
            "description": "A potential contamination event has been detected",
            "fields": ["alert_id", "zone", "contaminant_type", "severity", "affected_batches"],
        },
        {
            "name": "facility_inspection",
            "description": "A regulatory or internal facility inspection has occurred",
            "fields": ["inspection_id", "facility_id", "inspector", "score", "findings"],
        },
        {
            "name": "sanitation_completed",
            "description": "A sanitation cycle has been completed in a zone",
            "fields": ["zone", "completed_by", "completed_at", "method", "verified"],
        },
        {
            "name": "recall_initiated",
            "description": "A product recall has been initiated",
            "fields": ["recall_id", "product_id", "batch_ids", "reason", "scope"],
        },
        {
            "name": "waste_recorded",
            "description": "Food waste has been recorded for a zone or product",
            "fields": ["zone", "product_id", "quantity_lbs", "reason", "waste_pct"],
        },
        {
            "name": "compliance_audit",
            "description": "A food safety compliance audit has been completed",
            "fields": ["audit_id", "facility_id", "auditor", "score", "non_conformances"],
        },
    ],
    rule_templates=[
        {
            "name": "Cold Storage Excursion",
            "type": "threshold",
            "expression": "event.temperature_f > 41 for 5m per unit_id",
            "severity": "critical",
            "description": "Critical alert when cooler temperature exceeds 41°F for 5 minutes",
        },
        {
            "name": "Freezer Excursion",
            "type": "threshold",
            "expression": "event.temperature_f > 0 for 5m per unit_id",
            "severity": "critical",
            "description": "Critical alert when freezer temperature exceeds 0°F for 5 minutes",
        },
        {
            "name": "Humidity Out of Range",
            "type": "threshold",
            "expression": "event.humidity_pct > 70 for 15m per zone",
            "severity": "high",
            "description": "Alert when humidity exceeds 70% for 15 minutes in a storage zone",
        },
        {
            "name": "Supplier Delivery Late",
            "type": "threshold",
            "expression": "event.delay_minutes > 120 per supplier_id",
            "severity": "high",
            "description": "Alert when a supplier delivery is more than 2 hours past its window",
        },
        {
            "name": "Quality Inspection Failed",
            "type": "threshold",
            "expression": "event.score < 85",
            "severity": "high",
            "description": "Alert when a quality inspection score falls below 85",
        },
        {
            "name": "Shelf Life Approaching Expiry",
            "type": "threshold",
            "expression": "event.days_remaining < 3 per product_id",
            "severity": "medium",
            "description": "Alert when product shelf life has fewer than 3 days remaining",
        },
        {
            "name": "FSMA Compliance Gap",
            "type": "threshold",
            "expression": "event.score < 90 per facility_id",
            "severity": "critical",
            "description": "Critical alert when facility inspection score drops below FSMA threshold of 90",
        },
        {
            "name": "Contamination Detected",
            "type": "event",
            "expression": "on contamination_alert",
            "severity": "critical",
            "description": "Immediate critical alert when any contamination event is detected",
        },
        {
            "name": "Waste Above Threshold",
            "type": "threshold",
            "expression": "event.waste_pct > 5 for 3d per zone",
            "severity": "medium",
            "description": "Alert when waste percentage exceeds 5% for 3 consecutive days",
        },
        {
            "name": "Supplier Quality Declining",
            "type": "frequency",
            "expression": "count(quality_inspection{score < 85}) > 3 within 30d per supplier_id",
            "severity": "high",
            "description": "Alert when a supplier has more than 3 inspection failures in 30 days",
        },
        {
            "name": "Batch Hold Required",
            "type": "event",
            "expression": "on quality_inspection where quality_check == 'fail'",
            "severity": "high",
            "description": "Hold batch for review when a quality check fails",
        },
        {
            "name": "Sanitation Overdue",
            "type": "absence",
            "expression": "no sanitation_completed for 8h per zone",
            "severity": "medium",
            "description": "Alert when sanitation has not been completed within 8 hours for a zone",
        },
    ],
    prompt_templates=[
        {
            "name": "food_safety_query",
            "task_type": "query",
            "system_prompt": (
                "You are a food safety operations assistant. Answer questions about "
                "temperature compliance, FSMA regulations, supplier quality, and shelf "
                "life management using the provided operational data. Cite specific "
                "sensor readings, batch IDs, and inspection scores."
            ),
        },
        {
            "name": "supply_chain_analysis",
            "task_type": "analysis",
            "system_prompt": (
                "You are a food & beverage supply chain analyst. Analyse supplier "
                "performance, delivery patterns, quality trends, and inventory levels. "
                "Identify risks to product availability and quality. Provide actionable "
                "recommendations for supplier management and procurement."
            ),
        },
        {
            "name": "compliance_report",
            "task_type": "analysis",
            "system_prompt": (
                "You are a compliance reporting assistant. Generate food safety compliance "
                "summaries, inspection readiness assessments, and corrective action reports. "
                "Reference FSMA requirements, HACCP plans, and facility-specific audit "
                "history. Highlight gaps and recommend remediation steps."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "Active Excursions", "metric": "active_excursions", "format": "number", "target": 0},
            {"label": "Compliance Score", "metric": "compliance_score", "format": "percent", "target": 95},
            {"label": "Waste Rate", "metric": "waste_rate", "format": "percent", "target": 3},
            {"label": "Supplier On-Time %", "metric": "supplier_on_time_rate", "format": "percent", "target": 95},
        ],
        "chart_types": [
            {"type": "line", "title": "Temperature Compliance Trend", "metric": "compliance_score", "period": "30d"},
            {"type": "bar", "title": "Excursions by Zone", "metric": "excursion_count", "group_by": "zone"},
            {"type": "pie", "title": "Waste by Reason", "metric": "waste_quantity", "group_by": "reason"},
            {"type": "heatmap", "title": "Supplier Quality Heatmap", "metric": "inspection_score", "group_by": "supplier_id"},
        ],
    },
    document_templates=[
        "HACCP Plan",
        "FSMA Preventive Controls",
        "Supplier Quality Agreements",
        "Sanitation Standard Operating Procedures (SSOP)",
        "Recall Procedure",
        "Temperature Monitoring Log",
    ],
)

register_vertical(FOOD_BEVERAGE)

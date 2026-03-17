"""Cold Chain monitoring industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

COLD_CHAIN = VerticalPackage(
    name="cold_chain",
    display_name="Cold Chain & Temperature-Controlled Logistics",
    description=(
        "Temperature-controlled supply chain monitoring — real-time sensor data, "
        "compliance tracking, excursion detection, and chain of custody management."
    ),
    event_types=[
        {
            "name": "temperature_reading",
            "description": "A temperature sensor reading from a monitored asset",
            "fields": ["sensor_id", "asset_id", "temperature_c", "location", "zone"],
        },
        {
            "name": "humidity_reading",
            "description": "A humidity sensor reading from a monitored asset",
            "fields": ["sensor_id", "asset_id", "humidity_pct", "location", "zone"],
        },
        {
            "name": "door_opened",
            "description": "A monitored cold storage door has been opened",
            "fields": ["door_id", "asset_id", "location", "duration_seconds", "authorized"],
        },
        {
            "name": "shipment_loaded",
            "description": "Temperature-sensitive goods have been loaded for transport",
            "fields": ["shipment_id", "vehicle_id", "product_type", "required_temp_range", "quantity"],
        },
        {
            "name": "compliance_check",
            "description": "A cold chain compliance verification has been performed",
            "fields": ["check_type", "asset_id", "result", "inspector_id", "temperature_at_check"],
        },
        {
            "name": "excursion_detected",
            "description": "A temperature or humidity excursion has been detected",
            "fields": ["sensor_id", "asset_id", "excursion_type", "reading", "threshold", "duration_minutes"],
        },
        {
            "name": "calibration_due",
            "description": "A sensor is due for calibration",
            "fields": ["sensor_id", "last_calibration", "calibration_interval_days", "status"],
        },
        {
            "name": "chain_of_custody_transfer",
            "description": "A custody transfer has occurred for temperature-sensitive goods",
            "fields": ["shipment_id", "from_party", "to_party", "temperature_at_transfer", "condition"],
        },
    ],
    rule_templates=[
        {
            "name": "Temperature High Alert",
            "type": "threshold",
            "expression": "event.temperature_c > upper_threshold",
            "severity": "critical",
            "description": "Alert when temperature exceeds the upper threshold for the zone",
        },
        {
            "name": "Temperature Low Alert",
            "type": "threshold",
            "expression": "event.temperature_c < lower_threshold",
            "severity": "critical",
            "description": "Alert when temperature drops below the lower threshold",
        },
        {
            "name": "Humidity Out of Range",
            "type": "threshold",
            "expression": "event.humidity_pct < 30 OR event.humidity_pct > 70",
            "severity": "high",
            "description": "Alert when humidity falls outside acceptable range",
        },
        {
            "name": "Prolonged Door Opening",
            "type": "threshold",
            "expression": "event.duration_seconds > 300",
            "severity": "high",
            "description": "Alert when a cold storage door remains open for more than 5 minutes",
        },
        {
            "name": "Excursion Duration Warning",
            "type": "threshold",
            "expression": "event.duration_minutes > 15",
            "severity": "critical",
            "description": "Critical alert when a temperature excursion exceeds 15 minutes",
        },
        {
            "name": "Sensor Calibration Overdue",
            "type": "threshold",
            "expression": "days_since_calibration > calibration_interval_days",
            "severity": "medium",
            "description": "Alert when a sensor is overdue for calibration",
        },
        {
            "name": "Compliance Check Failure",
            "type": "threshold",
            "expression": "event.result == 'fail'",
            "severity": "critical",
            "description": "Immediate alert on any cold chain compliance failure",
        },
        {
            "name": "Custody Transfer Temperature Gap",
            "type": "threshold",
            "expression": "abs(event.temperature_at_transfer - required_temp) > 3",
            "severity": "high",
            "description": "Alert when temperature at custody transfer deviates more than 3C from requirement",
        },
    ],
    prompt_templates=[
        {
            "name": "cold_chain_query",
            "task_type": "query",
            "system_prompt": (
                "You are a cold chain operations intelligence assistant. Answer questions "
                "about temperature monitoring, compliance status, excursion history, and "
                "sensor health. Always specify temperatures in Celsius with one decimal "
                "place and reference specific sensor and asset IDs."
            ),
        },
        {
            "name": "excursion_analysis",
            "task_type": "analysis",
            "system_prompt": (
                "Analyse temperature excursion data to identify root causes, patterns, "
                "and risk factors. Assess product impact based on excursion duration and "
                "severity. Recommend corrective actions and preventive measures aligned "
                "with GDP (Good Distribution Practice) guidelines."
            ),
        },
        {
            "name": "compliance_report",
            "task_type": "analysis",
            "system_prompt": (
                "Generate a cold chain compliance report based on the provided monitoring "
                "data. Verify adherence to regulatory requirements (FDA 21 CFR Part 211, "
                "EU GDP Annex 15). Flag non-conformances and recommend remediation steps."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "Compliance Rate", "metric": "compliance_rate", "format": "percent", "target": 99.5},
            {"label": "Active Excursions", "metric": "active_excursions", "format": "number", "target": 0},
            {"label": "Avg Temperature (C)", "metric": "avg_temperature", "format": "decimal"},
            {"label": "Sensors Online", "metric": "sensors_online_pct", "format": "percent", "target": 100},
        ],
        "chart_types": [
            {"type": "line", "title": "Temperature Trend (24h)", "metric": "avg_temperature", "period": "24h"},
            {"type": "bar", "title": "Excursions by Zone", "metric": "excursion_count", "group_by": "zone"},
            {"type": "line", "title": "Humidity Trend", "metric": "avg_humidity", "period": "24h"},
            {"type": "heatmap", "title": "Temperature Heatmap by Asset", "metric": "temperature", "group_by": "asset_id"},
        ],
    },
    document_templates=[
        "Temperature Monitoring SOPs",
        "Excursion Response Procedures",
        "Sensor Calibration Records",
        "GDP Compliance Checklists",
        "Chain of Custody Forms",
        "Regulatory Audit Preparation Guide",
    ],
)

register_vertical(COLD_CHAIN)

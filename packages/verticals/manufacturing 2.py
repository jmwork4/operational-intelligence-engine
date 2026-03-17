"""Manufacturing industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

MANUFACTURING = VerticalPackage(
    name="manufacturing",
    display_name="Manufacturing & Production",
    description=(
        "Factory floor and production operations monitoring — production tracking, "
        "quality control, equipment health, material management, and shift coordination."
    ),
    event_types=[
        {
            "name": "production_started",
            "description": "A production run has started on a line",
            "fields": ["line_id", "product_id", "batch_id", "target_quantity", "operator_id"],
        },
        {
            "name": "production_completed",
            "description": "A production run has completed",
            "fields": ["line_id", "product_id", "batch_id", "actual_quantity", "duration_minutes"],
        },
        {
            "name": "quality_check_failed",
            "description": "A quality inspection has identified a defect",
            "fields": ["line_id", "batch_id", "defect_type", "severity", "inspector_id"],
        },
        {
            "name": "equipment_fault",
            "description": "An equipment fault or malfunction has been detected",
            "fields": ["equipment_id", "fault_code", "severity", "line_id", "description"],
        },
        {
            "name": "material_received",
            "description": "Raw materials have been received at the facility",
            "fields": ["material_id", "supplier_id", "quantity", "quality_grade", "po_number"],
        },
        {
            "name": "shift_started",
            "description": "A production shift has started",
            "fields": ["shift_id", "line_id", "supervisor_id", "crew_size", "planned_output"],
        },
        {
            "name": "maintenance_scheduled",
            "description": "Preventive maintenance has been scheduled",
            "fields": ["equipment_id", "maintenance_type", "scheduled_date", "estimated_downtime_hours"],
        },
        {
            "name": "output_below_target",
            "description": "Production output has fallen below target",
            "fields": ["line_id", "shift_id", "target_quantity", "actual_quantity", "variance_pct"],
        },
        {
            "name": "scrap_recorded",
            "description": "Scrap or waste material has been recorded",
            "fields": ["line_id", "batch_id", "scrap_quantity", "reason", "cost_estimate"],
        },
        {
            "name": "line_stopped",
            "description": "A production line has been stopped",
            "fields": ["line_id", "reason", "expected_restart", "impact_assessment"],
        },
    ],
    rule_templates=[
        {
            "name": "Production Below Target",
            "type": "threshold",
            "expression": "event.variance_pct > 10",
            "severity": "high",
            "description": "Alert when production output falls more than 10% below target",
        },
        {
            "name": "Quality Defect Rate",
            "type": "frequency",
            "expression": "count(quality_check_failed) > 5 within 1h per line_id",
            "severity": "critical",
            "description": "Alert when quality defect rate spikes on a production line",
        },
        {
            "name": "Equipment Fault Critical",
            "type": "threshold",
            "expression": "event.severity == 'critical'",
            "severity": "critical",
            "description": "Immediate alert for critical equipment faults",
        },
        {
            "name": "Line Stoppage",
            "type": "threshold",
            "expression": "event_type == 'line_stopped'",
            "severity": "critical",
            "description": "Alert on any unplanned production line stoppage",
        },
        {
            "name": "Scrap Rate Warning",
            "type": "threshold",
            "expression": "scrap_rate > 5",
            "severity": "medium",
            "description": "Alert when scrap rate exceeds 5% of production",
        },
        {
            "name": "Maintenance Overdue",
            "type": "absence",
            "expression": "no maintenance_scheduled for 30d per equipment_id",
            "severity": "medium",
            "description": "Alert when equipment maintenance is overdue",
        },
        {
            "name": "Material Shortage Risk",
            "type": "threshold",
            "expression": "inventory_level < reorder_point",
            "severity": "high",
            "description": "Alert when raw material inventory drops below reorder point",
        },
        {
            "name": "OEE Below Threshold",
            "type": "threshold",
            "expression": "oee_score < 65",
            "severity": "high",
            "description": "Alert when Overall Equipment Effectiveness drops below 65%",
        },
    ],
    prompt_templates=[
        {
            "name": "manufacturing_query",
            "task_type": "query",
            "system_prompt": (
                "You are a manufacturing operations intelligence assistant. Answer questions "
                "about production performance, equipment status, quality metrics, and material "
                "availability. Use specific line IDs, batch numbers, and metrics in your responses."
            ),
        },
        {
            "name": "production_analysis",
            "task_type": "analysis",
            "system_prompt": (
                "Analyse production data to identify efficiency gaps, quality trends, and "
                "equipment reliability patterns. Calculate OEE components (availability, "
                "performance, quality) and recommend improvement actions."
            ),
        },
        {
            "name": "maintenance_planning",
            "task_type": "analysis",
            "system_prompt": (
                "Review equipment fault history and maintenance records to recommend an "
                "optimised preventive maintenance schedule. Identify equipment at risk of "
                "failure and estimate downtime impact on production targets."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "OEE Score", "metric": "oee_score", "format": "percent", "target": 85},
            {"label": "Production Output", "metric": "daily_output", "format": "number"},
            {"label": "Defect Rate", "metric": "defect_rate", "format": "percent", "target": 2},
            {"label": "Equipment Uptime", "metric": "equipment_uptime", "format": "percent", "target": 95},
        ],
        "chart_types": [
            {"type": "line", "title": "OEE Trend", "metric": "oee_score", "period": "30d"},
            {"type": "bar", "title": "Output by Production Line", "metric": "output", "group_by": "line_id"},
            {"type": "pie", "title": "Defects by Type", "metric": "defect_count", "group_by": "defect_type"},
            {"type": "bar", "title": "Downtime by Cause", "metric": "downtime_hours", "group_by": "reason"},
        ],
    },
    document_templates=[
        "Standard Operating Procedures (SOP)",
        "Quality Control Checklists",
        "Equipment Maintenance Manuals",
        "Safety Data Sheets (SDS)",
        "Production Scheduling Guidelines",
        "Lean Manufacturing Playbooks",
    ],
)

register_vertical(MANUFACTURING)

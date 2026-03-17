"""Healthcare operations industry vertical package for OIE."""

from packages.verticals.base import VerticalPackage, register_vertical

HEALTHCARE = VerticalPackage(
    name="healthcare",
    display_name="Healthcare Operations",
    description=(
        "Hospital and healthcare facility operations monitoring — patient flow, "
        "bed management, equipment tracking, compliance, and staff coordination."
    ),
    event_types=[
        {
            "name": "patient_admitted",
            "description": "A patient has been admitted to the facility",
            "fields": ["patient_id", "department", "bed_id", "admitting_physician", "priority"],
        },
        {
            "name": "patient_discharged",
            "description": "A patient has been discharged from the facility",
            "fields": ["patient_id", "department", "discharge_type", "length_of_stay_hours"],
        },
        {
            "name": "bed_assigned",
            "description": "A bed has been assigned or reassigned",
            "fields": ["bed_id", "ward", "patient_id", "status", "cleaning_status"],
        },
        {
            "name": "equipment_alert",
            "description": "A medical equipment alert has been triggered",
            "fields": ["equipment_id", "equipment_type", "alert_type", "location", "severity"],
        },
        {
            "name": "medication_dispensed",
            "description": "Medication has been dispensed to a patient",
            "fields": ["patient_id", "medication", "dosage", "dispensed_by", "timestamp"],
        },
        {
            "name": "nurse_call",
            "description": "A nurse call has been activated",
            "fields": ["bed_id", "ward", "patient_id", "call_type", "priority"],
        },
        {
            "name": "lab_result",
            "description": "A laboratory result has been received",
            "fields": ["patient_id", "test_type", "result", "status", "critical_flag"],
        },
        {
            "name": "compliance_check",
            "description": "A compliance or regulatory check has been performed",
            "fields": ["check_type", "department", "result", "inspector_id", "notes"],
        },
        {
            "name": "shift_change",
            "description": "A staff shift change has occurred",
            "fields": ["department", "outgoing_staff", "incoming_staff", "handoff_notes"],
        },
        {
            "name": "incident_reported",
            "description": "A safety or operational incident has been reported",
            "fields": ["incident_type", "department", "severity", "reporter_id", "description"],
        },
    ],
    rule_templates=[
        {
            "name": "Bed Capacity Warning",
            "type": "threshold",
            "expression": "bed_occupancy_rate > 90",
            "severity": "high",
            "description": "Alert when bed occupancy exceeds 90% in a ward",
        },
        {
            "name": "Critical Lab Result",
            "type": "threshold",
            "expression": "event.critical_flag == true",
            "severity": "critical",
            "description": "Immediate alert for critical laboratory results",
        },
        {
            "name": "Equipment Malfunction",
            "type": "threshold",
            "expression": "event.alert_type == 'malfunction'",
            "severity": "high",
            "description": "Alert when medical equipment reports a malfunction",
        },
        {
            "name": "Nurse Call Response Time",
            "type": "threshold",
            "expression": "response_time_minutes > 5",
            "severity": "medium",
            "description": "Alert when nurse call response exceeds 5 minutes",
        },
        {
            "name": "Patient Wait Time",
            "type": "threshold",
            "expression": "wait_time_minutes > 60",
            "severity": "high",
            "description": "Alert when patient wait time exceeds 1 hour",
        },
        {
            "name": "Compliance Failure",
            "type": "threshold",
            "expression": "event.result == 'fail'",
            "severity": "critical",
            "description": "Alert on any compliance check failure",
        },
        {
            "name": "Medication Timing Alert",
            "type": "absence",
            "expression": "no medication_dispensed for 2h per patient_id where scheduled",
            "severity": "high",
            "description": "Alert when scheduled medication has not been dispensed",
        },
        {
            "name": "Incident Escalation",
            "type": "threshold",
            "expression": "event.severity in ('critical', 'high')",
            "severity": "critical",
            "description": "Escalate high-severity safety incidents immediately",
        },
    ],
    prompt_templates=[
        {
            "name": "healthcare_query",
            "task_type": "query",
            "system_prompt": (
                "You are a healthcare operations intelligence assistant. Answer questions "
                "about patient flow, bed availability, equipment status, and compliance. "
                "Always respect patient privacy — refer to patients by ID only. Be precise "
                "with medical terminology and provide evidence-based recommendations."
            ),
        },
        {
            "name": "patient_flow_analysis",
            "task_type": "analysis",
            "system_prompt": (
                "Analyse patient flow data to identify bottlenecks, predict capacity issues, "
                "and recommend staffing adjustments. Focus on admission-to-discharge timelines, "
                "bed turnover rates, and department-level throughput."
            ),
        },
        {
            "name": "compliance_report",
            "task_type": "analysis",
            "system_prompt": (
                "Generate a compliance status report based on the provided check results. "
                "Highlight failures, near-misses, and trends. Recommend corrective actions "
                "aligned with regulatory requirements (HIPAA, Joint Commission, CMS)."
            ),
        },
    ],
    dashboard_config={
        "kpi_cards": [
            {"label": "Bed Occupancy Rate", "metric": "bed_occupancy_rate", "format": "percent", "target": 85},
            {"label": "Avg Wait Time (min)", "metric": "avg_wait_minutes", "format": "number", "target": 30},
            {"label": "Active Patients", "metric": "active_patients", "format": "number"},
            {"label": "Compliance Score", "metric": "compliance_score", "format": "percent", "target": 98},
        ],
        "chart_types": [
            {"type": "line", "title": "Patient Admissions Trend", "metric": "admission_count", "period": "30d"},
            {"type": "bar", "title": "Incidents by Department", "metric": "incident_count", "group_by": "department"},
            {"type": "pie", "title": "Bed Status Distribution", "metric": "bed_count", "group_by": "status"},
            {"type": "gauge", "title": "Overall Compliance", "metric": "compliance_score"},
        ],
    },
    document_templates=[
        "Clinical Protocols",
        "Emergency Procedures",
        "HIPAA Compliance Guidelines",
        "Equipment Maintenance Schedules",
        "Staff Training Records",
        "Incident Response Plans",
    ],
)

register_vertical(HEALTHCARE)

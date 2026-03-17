"""Pre-built workflow templates for common operational scenarios."""

from __future__ import annotations

from uuid import UUID

from packages.workflows.engine import WorkflowDefinition, WorkflowStep


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

CRITICAL_ALERT_WORKFLOW = WorkflowDefinition(
    id=UUID("00000000-0000-0000-0000-000000000001"),
    name="Critical Alert Escalation",
    trigger={
        "alert_severity": "critical",
    },
    steps=[
        WorkflowStep(
            step_type="notify",
            config={
                "channel": "slack",
                "target": "#ops-critical",
                "message": "CRITICAL ALERT: {rule_name} on {entity_id} — {message}",
            },
            timeout_seconds=30,
        ),
        WorkflowStep(
            step_type="notify",
            config={
                "channel": "pagerduty",
                "target": "ops-oncall",
                "message": "Critical: {rule_name} — {entity_id}",
            },
            timeout_seconds=30,
        ),
        WorkflowStep(
            step_type="delay",
            config={"minutes": 15},
            timeout_seconds=960,
        ),
        WorkflowStep(
            step_type="notify",
            config={
                "channel": "email",
                "target": "ops-manager@company.com",
                "message": (
                    "ESCALATION: Critical alert {rule_name} on {entity_id} "
                    "has not been acknowledged after 15 minutes. "
                    "Details: {message}"
                ),
            },
            condition="severity == critical",
            timeout_seconds=30,
        ),
    ],
    enabled=True,
)


SLA_BREACH_WORKFLOW = WorkflowDefinition(
    id=UUID("00000000-0000-0000-0000-000000000002"),
    name="SLA Breach Response",
    trigger={
        "alert_rule_id": "sla_breach",
        "event_type": "delivery_sla_breach",
    },
    steps=[
        WorkflowStep(
            step_type="ai_analyze",
            config={
                "analysis_type": "sla_breach",
            },
            timeout_seconds=60,
        ),
        WorkflowStep(
            step_type="notify",
            config={
                "channel": "email",
                "target": "customer-success@company.com",
                "message": (
                    "SLA Breach Detected for {entity_id}. "
                    "An AI analysis has been generated. "
                    "Please review and reach out to the customer."
                ),
            },
            timeout_seconds=30,
        ),
        WorkflowStep(
            step_type="api_call",
            config={
                "url": "https://tickets.example.com/api/tickets",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "title": "SLA Breach — {entity_id}",
                    "priority": "high",
                    "category": "sla_breach",
                    "description": "Automated ticket for SLA breach alert.",
                },
            },
            timeout_seconds=30,
        ),
        WorkflowStep(
            step_type="notify",
            config={
                "channel": "slack",
                "target": "#ops-sla",
                "message": "SLA breach for {entity_id} — ticket created, customer notified.",
            },
            timeout_seconds=30,
        ),
    ],
    enabled=True,
)


MAINTENANCE_DUE_WORKFLOW = WorkflowDefinition(
    id=UUID("00000000-0000-0000-0000-000000000003"),
    name="Maintenance Due Workflow",
    trigger={
        "event_type": "maintenance_due",
    },
    steps=[
        WorkflowStep(
            step_type="api_call",
            config={
                "url": "https://tickets.example.com/api/tickets",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "title": "Scheduled Maintenance — {entity_id}",
                    "priority": "medium",
                    "category": "maintenance",
                    "description": "Preventive maintenance is due for {entity_id}.",
                },
            },
            timeout_seconds=30,
        ),
        WorkflowStep(
            step_type="notify",
            config={
                "channel": "email",
                "target": "fleet-manager@company.com",
                "message": (
                    "Maintenance due for {entity_id}. "
                    "A ticket has been created. Please schedule within 24 hours."
                ),
            },
            timeout_seconds=30,
        ),
        WorkflowStep(
            step_type="delay",
            config={"seconds": 5},  # In production: {"hours": 24}
            timeout_seconds=90000,
        ),
        WorkflowStep(
            step_type="api_call",
            config={
                "url": "https://tickets.example.com/api/tickets/{entity_id}/status",
                "method": "GET",
                "headers": {"Content-Type": "application/json"},
                "body": {},
            },
            timeout_seconds=30,
        ),
    ],
    enabled=True,
)


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

WORKFLOW_TEMPLATES: list[WorkflowDefinition] = [
    CRITICAL_ALERT_WORKFLOW,
    SLA_BREACH_WORKFLOW,
    MAINTENANCE_DUE_WORKFLOW,
]


def get_workflow_templates() -> list[WorkflowDefinition]:
    """Return all pre-built workflow templates."""
    return list(WORKFLOW_TEMPLATES)

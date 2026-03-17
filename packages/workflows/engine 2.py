"""OIE Workflow Automation Engine — execute multi-step operational workflows."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """A single step in a workflow definition.

    Supported step types
    --------------------
    - ``notify`` — Send notification via integration (slack, email, sms).
    - ``api_call`` — Make HTTP request to an external API.
    - ``approve`` — Wait for human approval before continuing.
    - ``delay`` — Wait N seconds/minutes.
    - ``ai_analyze`` — Run AI analysis on the triggering alert.
    """

    step_type: str
    config: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    timeout_seconds: int = 300


@dataclass
class WorkflowDefinition:
    """Complete workflow definition with trigger and steps."""

    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    name: str = ""
    trigger: dict[str, Any] = field(default_factory=dict)
    steps: list[WorkflowStep] = field(default_factory=list)
    enabled: bool = True


@dataclass
class StepResult:
    """Result of executing a single workflow step."""

    step_type: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class WorkflowExecution:
    """Record of a workflow execution."""

    workflow_id: UUID = field(default_factory=uuid4)
    trigger_data: dict[str, Any] = field(default_factory=dict)
    steps_completed: int = 0
    steps_total: int = 0
    status: str = "running"  # running | completed | failed
    results: list[StepResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class WorkflowEngine:
    """Execute multi-step operational workflows.

    The engine processes :class:`WorkflowDefinition` instances by running
    each :class:`WorkflowStep` sequentially.  Each step is dispatched to a
    type-specific handler.  Failed steps are logged and, depending on the
    step configuration, the workflow either continues or aborts.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {
            "notify": self._handle_notify,
            "api_call": self._handle_api_call,
            "approve": self._handle_approve,
            "delay": self._handle_delay,
            "ai_analyze": self._handle_ai_analyze,
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        trigger_data: dict[str, Any],
    ) -> WorkflowExecution:
        """Execute all steps of a workflow sequentially.

        Parameters
        ----------
        workflow:
            The workflow definition to run.
        trigger_data:
            Data from the event or alert that triggered this workflow.

        Returns
        -------
        WorkflowExecution:
            Full execution record including per-step results.
        """
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            trigger_data=trigger_data,
            steps_total=len(workflow.steps),
        )

        logger.info(
            "Starting workflow execution",
            extra={"workflow": workflow.name, "steps": len(workflow.steps)},
        )

        context: dict[str, Any] = {
            "trigger": trigger_data,
            "workflow_name": workflow.name,
            "step_results": [],
        }

        for i, step in enumerate(workflow.steps):
            # Evaluate condition if present
            if step.condition and not self._evaluate_condition(step.condition, context):
                logger.info("Skipping step %d — condition not met", i + 1)
                execution.results.append(StepResult(
                    step_type=step.step_type,
                    success=True,
                    result={"skipped": True, "reason": "condition_not_met"},
                ))
                execution.steps_completed += 1
                continue

            result = await self.execute_step(step, context)
            execution.results.append(result)
            context["step_results"].append(result)
            execution.steps_completed += 1

            if not result.success:
                abort = step.config.get("abort_on_failure", False)
                if abort:
                    logger.warning(
                        "Step %d failed — aborting workflow", i + 1,
                        extra={"error": result.error},
                    )
                    execution.status = "failed"
                    execution.completed_at = datetime.now(timezone.utc)
                    return execution
                else:
                    logger.warning(
                        "Step %d failed — continuing", i + 1,
                        extra={"error": result.error},
                    )

        execution.status = "completed"
        execution.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Workflow execution completed",
            extra={
                "workflow": workflow.name,
                "status": execution.status,
                "steps_completed": execution.steps_completed,
            },
        )

        return execution

    async def execute_step(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> StepResult:
        """Execute a single workflow step.

        Routes to the appropriate handler based on ``step.step_type``.
        """
        handler = self._handlers.get(step.step_type)
        if handler is None:
            return StepResult(
                step_type=step.step_type,
                success=False,
                error=f"Unknown step type: {step.step_type}",
            )

        start = time.monotonic()
        try:
            result_data = await asyncio.wait_for(
                handler(step, context),
                timeout=step.timeout_seconds,
            )
            duration_ms = (time.monotonic() - start) * 1000
            return StepResult(
                step_type=step.step_type,
                success=True,
                result=result_data,
                duration_ms=round(duration_ms, 2),
            )
        except asyncio.TimeoutError:
            duration_ms = (time.monotonic() - start) * 1000
            return StepResult(
                step_type=step.step_type,
                success=False,
                error=f"Step timed out after {step.timeout_seconds}s",
                duration_ms=round(duration_ms, 2),
            )
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            return StepResult(
                step_type=step.step_type,
                success=False,
                error=str(exc),
                duration_ms=round(duration_ms, 2),
            )

    # ------------------------------------------------------------------ #
    # Step handlers
    # ------------------------------------------------------------------ #

    async def _handle_notify(
        self, step: WorkflowStep, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a notification via the configured integration."""
        channel = step.config.get("channel", "unknown")
        target = step.config.get("target", "")
        message = step.config.get("message", "Workflow notification")

        # Template the message with trigger data
        trigger = context.get("trigger", {})
        try:
            message = message.format(**trigger)
        except (KeyError, IndexError):
            pass

        logger.info(
            "Sending notification",
            extra={"channel": channel, "target": target},
        )

        # In production this would dispatch to Slack/email/SMS integrations
        return {
            "channel": channel,
            "target": target,
            "message": message,
            "delivered": True,
        }

    async def _handle_api_call(
        self, step: WorkflowStep, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Make an HTTP request to an external API."""
        url = step.config.get("url", "")
        method = step.config.get("method", "POST").upper()
        headers = step.config.get("headers", {})
        body = step.config.get("body", {})

        logger.info("Making API call", extra={"url": url, "method": method})

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=body,
                headers=headers,
                timeout=step.timeout_seconds,
            )

        return {
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "response_body": response.text[:500],
        }

    async def _handle_approve(
        self, step: WorkflowStep, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Wait for human approval.

        In production, this would create an approval request and poll/wait
        for a response.  For now, auto-approves after a brief delay.
        """
        approver = step.config.get("approver", "ops-team")
        logger.info("Awaiting approval from %s", approver)

        # Simulated approval — in production this integrates with an
        # approval queue / Slack interactive message / etc.
        await asyncio.sleep(1)

        return {
            "approver": approver,
            "approved": True,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_delay(
        self, step: WorkflowStep, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Wait for a specified duration."""
        seconds = step.config.get("seconds", 0)
        minutes = step.config.get("minutes", 0)
        total_seconds = seconds + (minutes * 60)

        logger.info("Delaying for %d seconds", total_seconds)
        await asyncio.sleep(total_seconds)

        return {"delayed_seconds": total_seconds}

    async def _handle_ai_analyze(
        self, step: WorkflowStep, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Run AI analysis on the triggering alert/event.

        In production, this calls the AI Service with appropriate context.
        For now, returns a template-based analysis summary.
        """
        trigger = context.get("trigger", {})
        analysis_type = step.config.get("analysis_type", "general")

        logger.info("Running AI analysis", extra={"type": analysis_type})

        severity = trigger.get("severity", "unknown")
        entity_id = trigger.get("entity_id", "N/A")
        message = trigger.get("message", "No details")

        return {
            "analysis_type": analysis_type,
            "summary": (
                f"AI analysis of {severity} alert for {entity_id}: {message}. "
                "Recommend reviewing correlated events and adjusting thresholds "
                "if this is a recurring pattern."
            ),
            "confidence": 0.85,
            "recommendations": [
                "Review alert rule threshold settings",
                "Check for correlated alerts in the last hour",
                "Verify entity operational status",
            ],
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a simple condition string against the context.

        Supports basic expressions like:
        - ``"severity == critical"``
        - ``"steps[-1].success == true"``

        For safety, uses simple string matching rather than ``eval``.
        """
        trigger = context.get("trigger", {})
        step_results = context.get("step_results", [])

        # Simple key-value checks
        if "==" in condition:
            key, value = [s.strip() for s in condition.split("==", 1)]
            actual = trigger.get(key)
            if actual is not None:
                return str(actual).lower() == value.lower()

        # Check last step result
        if "steps[-1].success" in condition:
            if step_results:
                last = step_results[-1]
                expected = "true" in condition.lower()
                return last.success == expected

        # Default: condition met
        return True

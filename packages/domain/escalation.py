"""Alert escalation system — policies, on-call rotations, quiet hours, and SLA tracking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from packages.common import utc_now


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class EscalationStage:
    """A single stage in an escalation policy."""

    wait_minutes: int
    channels: list[dict]  # e.g. [{"type": "slack", "url": "..."}, {"type": "email", "to": "mgr@co.com"}]
    notify_role: str | None = None


@dataclass
class EscalationPolicy:
    """Defines how alerts escalate over time."""

    id: UUID
    tenant_id: UUID
    name: str
    severity_filter: list[str]
    stages: list[EscalationStage]


@dataclass
class OnCallRotation:
    """On-call rotation schedule."""

    id: UUID
    tenant_id: UUID
    name: str
    members: list[dict]  # [{"user_id": "...", "name": "...", "order": 0}]
    current_index: int = 0
    rotation_type: Literal["daily", "weekly"] = "daily"


@dataclass
class QuietHours:
    """Quiet-hours configuration for a tenant."""

    tenant_id: UUID
    start_hour: int  # 0-23 in the given timezone
    end_hour: int  # 0-23 in the given timezone
    timezone: str  # e.g. "America/New_York"
    severity_override: list[str] = field(default_factory=lambda: ["critical"])


@dataclass
class AlertGroup:
    """A group of correlated alerts."""

    id: UUID
    tenant_id: UUID
    name: str
    alert_ids: list[UUID]
    root_alert_id: UUID
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class EscalationAction:
    """Action to take for an escalation."""

    stage: int
    channels: list[dict]
    message: str


@dataclass
class SLAMetrics:
    """SLA tracking metrics for a single alert."""

    time_to_acknowledge_minutes: float | None
    time_to_resolve_minutes: float | None
    sla_target_minutes: float
    breached: bool


# ---------------------------------------------------------------------------
# Escalation service
# ---------------------------------------------------------------------------


class EscalationService:
    """Manages alert escalation, grouping, on-call rotations, and SLA tracking."""

    async def check_escalation(
        self, alert: dict, policy: EscalationPolicy
    ) -> EscalationAction | None:
        """Check whether an alert should escalate based on the policy.

        Parameters
        ----------
        alert:
            A dict with at least ``severity``, ``status``, ``created_at``
            (ISO-8601 string or datetime), and optionally ``acknowledged_at``.
        policy:
            The escalation policy to evaluate against.

        Returns
        -------
        EscalationAction | None
            The action to take, or *None* if no escalation is needed.
        """
        # Only escalate alerts matching the policy severity filter
        alert_severity = alert.get("severity", "")
        if policy.severity_filter and alert_severity not in policy.severity_filter:
            return None

        # Already acknowledged — no escalation
        if alert.get("status") in ("acknowledged", "resolved"):
            return None

        # Determine how long the alert has been unacknowledged
        created_at = alert.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if created_at is None:
            return None

        now = utc_now()
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        elapsed_minutes = (now - created_at).total_seconds() / 60

        # Walk through stages and find the applicable one
        applicable_stage: int | None = None
        applicable_stage_obj: EscalationStage | None = None

        for idx, stage in enumerate(policy.stages):
            if elapsed_minutes >= stage.wait_minutes:
                applicable_stage = idx
                applicable_stage_obj = stage

        if applicable_stage is None or applicable_stage_obj is None:
            return None

        return EscalationAction(
            stage=applicable_stage,
            channels=applicable_stage_obj.channels,
            message=(
                f"Alert escalated to stage {applicable_stage + 1} "
                f"({applicable_stage_obj.notify_role or 'default'}) — "
                f"unacknowledged for {int(elapsed_minutes)} minutes"
            ),
        )

    async def is_quiet_hours(self, quiet_hours: QuietHours) -> bool:
        """Check whether the current time falls within quiet hours.

        Parameters
        ----------
        quiet_hours:
            The quiet-hours configuration to evaluate.

        Returns
        -------
        bool
            True if currently within quiet hours.
        """
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(quiet_hours.timezone)
        except Exception:
            tz = timezone.utc

        now_local = datetime.now(tz)
        current_hour = now_local.hour

        if quiet_hours.start_hour <= quiet_hours.end_hour:
            # Same-day window, e.g. 22–23
            return quiet_hours.start_hour <= current_hour < quiet_hours.end_hour
        else:
            # Overnight window, e.g. 22–06
            return current_hour >= quiet_hours.start_hour or current_hour < quiet_hours.end_hour

    async def should_notify(
        self, alert: dict, quiet_hours: QuietHours | None
    ) -> bool:
        """Return True if the alert should trigger a notification (respecting quiet hours)."""
        if quiet_hours is None:
            return True

        severity = alert.get("severity", "")
        # Severity overrides bypass quiet hours
        if severity in quiet_hours.severity_override:
            return True

        in_quiet = await self.is_quiet_hours(quiet_hours)
        return not in_quiet

    async def group_alerts(
        self,
        tenant_id: UUID,
        alerts: list[dict],
        time_window_minutes: int = 30,
    ) -> list[AlertGroup]:
        """Group alerts by entity_id + rule_id within a time window.

        Parameters
        ----------
        tenant_id:
            The tenant that owns the alerts.
        alerts:
            A list of alert dicts, each containing at least ``id``,
            ``entity_id``, ``rule_id``, and ``created_at``.
        time_window_minutes:
            Maximum gap between alerts in the same group.
        """
        # Sort by created_at
        def _parse_dt(a: dict) -> datetime:
            v = a.get("created_at")
            if isinstance(v, str):
                return datetime.fromisoformat(v)
            if isinstance(v, datetime):
                return v
            return datetime.min.replace(tzinfo=timezone.utc)

        sorted_alerts = sorted(alerts, key=_parse_dt)

        # Bucket by (entity_id, rule_id)
        buckets: dict[tuple[str, str], list[dict]] = {}
        for alert in sorted_alerts:
            key = (str(alert.get("entity_id", "")), str(alert.get("rule_id", "")))
            buckets.setdefault(key, []).append(alert)

        groups: list[AlertGroup] = []
        window = timedelta(minutes=time_window_minutes)

        for (entity_id, rule_id), bucket in buckets.items():
            # Split bucket into sub-groups when the gap exceeds the window
            current_group: list[dict] = [bucket[0]]
            for i in range(1, len(bucket)):
                prev_dt = _parse_dt(bucket[i - 1])
                curr_dt = _parse_dt(bucket[i])
                if (curr_dt - prev_dt) <= window:
                    current_group.append(bucket[i])
                else:
                    groups.append(self._make_group(tenant_id, entity_id, rule_id, current_group))
                    current_group = [bucket[i]]
            groups.append(self._make_group(tenant_id, entity_id, rule_id, current_group))

        return groups

    def _make_group(
        self, tenant_id: UUID, entity_id: str, rule_id: str, alerts: list[dict]
    ) -> AlertGroup:
        alert_ids = [UUID(str(a["id"])) for a in alerts]
        return AlertGroup(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=f"Group: {entity_id} / {rule_id} ({len(alerts)} alerts)",
            alert_ids=alert_ids,
            root_alert_id=alert_ids[0],
        )

    async def get_current_oncall(self, rotation: OnCallRotation) -> dict:
        """Return the current on-call person based on rotation type and date.

        For ``daily`` rotations the index advances every day; for ``weekly``
        rotations it advances every 7 days.  The starting reference point is
        the epoch (1970-01-01).
        """
        if not rotation.members:
            return {}

        today = date.today()
        epoch = date(1970, 1, 1)
        days_since_epoch = (today - epoch).days

        if rotation.rotation_type == "weekly":
            period = days_since_epoch // 7
        else:
            period = days_since_epoch

        idx = (rotation.current_index + period) % len(rotation.members)
        return rotation.members[idx]


# ---------------------------------------------------------------------------
# SLA tracker
# ---------------------------------------------------------------------------


class SLATracker:
    """Tracks SLA compliance for alerts."""

    def __init__(self, sla_target_minutes: float = 60.0) -> None:
        self.sla_target_minutes = sla_target_minutes

    async def track(self, alert_id: UUID, tenant_id: UUID, alert: dict | None = None) -> SLAMetrics:
        """Compute SLA metrics for a given alert.

        Parameters
        ----------
        alert_id:
            The alert identifier.
        tenant_id:
            The tenant that owns the alert.
        alert:
            Optional pre-loaded alert dict containing ``created_at``,
            ``acknowledged_at``, ``resolved_at``.
        """
        if alert is None:
            # No data available — return empty metrics
            return SLAMetrics(
                time_to_acknowledge_minutes=None,
                time_to_resolve_minutes=None,
                sla_target_minutes=self.sla_target_minutes,
                breached=False,
            )

        def _to_dt(v: str | datetime | None) -> datetime | None:
            if v is None:
                return None
            if isinstance(v, str):
                return datetime.fromisoformat(v)
            return v

        created = _to_dt(alert.get("created_at"))
        acknowledged = _to_dt(alert.get("acknowledged_at"))
        resolved = _to_dt(alert.get("resolved_at"))

        tta: float | None = None
        ttr: float | None = None

        if created and acknowledged:
            tta = (acknowledged - created).total_seconds() / 60
        if created and resolved:
            ttr = (resolved - created).total_seconds() / 60

        # Breach: either still open beyond target, or resolution exceeded target
        now = utc_now()
        breached = False
        if ttr is not None:
            breached = ttr > self.sla_target_minutes
        elif created:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            elapsed = (now - created).total_seconds() / 60
            breached = elapsed > self.sla_target_minutes

        return SLAMetrics(
            time_to_acknowledge_minutes=tta,
            time_to_resolve_minutes=ttr,
            sla_target_minutes=self.sla_target_minutes,
            breached=breached,
        )

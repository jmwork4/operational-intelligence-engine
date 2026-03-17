"""Alert domain service — creation, deduplication, and lifecycle management."""

from __future__ import annotations

import hashlib
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import AlertStatus, utc_now
from packages.db.models.alert import Alert


class AlertService:
    """Manages alert creation, deduplication, and status transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Creation & deduplication
    # ------------------------------------------------------------------

    async def create_alert(
        self,
        tenant_id: UUID,
        rule_id: UUID,
        entity_type: str,
        entity_id: str,
        severity: str,
        message: str,
        context: dict,
        evaluation_window: int | None = None,
    ) -> Alert | None:
        """Create a new alert, suppressing duplicates.

        A dedup key is derived from tenant, rule, entity and evaluation
        window.  If an active alert with the same key already exists the
        call returns ``None`` (suppressed).
        """
        dedup_key = hashlib.sha256(
            f"{tenant_id}:{rule_id}:{entity_id}:{evaluation_window or 0}".encode()
        ).hexdigest()

        # Check for an existing active alert with the same dedup key.
        existing_stmt = sa.select(Alert).where(
            Alert.tenant_id == tenant_id,
            Alert.dedup_key == dedup_key,
            Alert.status == AlertStatus.ACTIVE,
        )
        result = await self._session.execute(existing_stmt)
        if result.scalar_one_or_none() is not None:
            return None  # suppressed duplicate

        alert = Alert(
            tenant_id=tenant_id,
            rule_id=rule_id,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            status=AlertStatus.ACTIVE,
            message=message,
            context=context,
            dedup_key=dedup_key,
        )
        self._session.add(alert)
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    async def acknowledge_alert(
        self, alert_id: UUID, tenant_id: UUID, user_id: UUID
    ) -> Alert:
        """Mark an alert as acknowledged by *user_id*."""
        alert = await self._load_alert(alert_id, tenant_id)
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user_id
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    async def resolve_alert(self, alert_id: UUID, tenant_id: UUID) -> Alert:
        """Mark an alert as resolved."""
        alert = await self._load_alert(alert_id, tenant_id)
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = utc_now()
        await self._session.commit()
        await self._session.refresh(alert)
        return alert

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_active_alerts(
        self, tenant_id: UUID, severity: str | None = None
    ) -> list[Alert]:
        """Return active alerts for a tenant, optionally filtered by severity."""
        stmt = (
            sa.select(Alert)
            .where(Alert.tenant_id == tenant_id, Alert.status == AlertStatus.ACTIVE)
        )
        if severity is not None:
            stmt = stmt.where(Alert.severity == severity)
        stmt = stmt.order_by(Alert.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_alert_stats(self, tenant_id: UUID) -> dict:
        """Return aggregate counts by severity and status for a tenant."""
        # Counts by status
        status_stmt = (
            sa.select(Alert.status, sa.func.count())
            .where(Alert.tenant_id == tenant_id)
            .group_by(Alert.status)
        )
        status_result = await self._session.execute(status_stmt)
        status_counts: dict[str, int] = {row[0]: row[1] for row in status_result.all()}

        # Counts by severity
        severity_stmt = (
            sa.select(Alert.severity, sa.func.count())
            .where(Alert.tenant_id == tenant_id)
            .group_by(Alert.severity)
        )
        severity_result = await self._session.execute(severity_stmt)
        by_severity: dict[str, int] = {row[0]: row[1] for row in severity_result.all()}

        total = sum(status_counts.values())

        return {
            "total": total,
            "active": status_counts.get(AlertStatus.ACTIVE, 0),
            "acknowledged": status_counts.get(AlertStatus.ACKNOWLEDGED, 0),
            "resolved": status_counts.get(AlertStatus.RESOLVED, 0),
            "by_severity": {
                "critical": by_severity.get("critical", 0),
                "high": by_severity.get("high", 0),
                "medium": by_severity.get("medium", 0),
                "low": by_severity.get("low", 0),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_alert(self, alert_id: UUID, tenant_id: UUID) -> Alert:
        """Load an alert and verify tenant ownership.

        Raises ``ResourceNotFoundError`` when no matching alert exists.
        """
        from packages.common import ResourceNotFoundError

        stmt = sa.select(Alert).where(
            Alert.id == alert_id, Alert.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert is None:
            raise ResourceNotFoundError("Alert", str(alert_id))
        return alert

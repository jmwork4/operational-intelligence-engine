"""Event routes — ingest and query operational events."""

from __future__ import annotations

import logging
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common import ResourceNotFoundError, get_settings, utc_now
from packages.db.models.event import Event
from packages.schemas import (
    EventBatchCreate,
    EventCreate,
    EventFilter,
    EventResponse,
    PaginatedResponse,
)

from apps.api.deps import RateLimiter, get_current_tenant, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def ingest_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> EventResponse:
    """Ingest a single operational event."""
    event = Event(
        tenant_id=tenant_id,
        event_type=body.event_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        source_system=body.source_system,
        payload=body.payload,
        metadata_=body.metadata,
        occurred_at=body.occurred_at or utc_now(),
    )
    if body.process_id is not None:
        event.process_id = UUID(body.process_id)
    if body.resource_id is not None:
        event.resource_id = UUID(body.resource_id)

    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Enqueue event for async processing (stream + rule evaluation)
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        settings = get_settings()
        arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await arq_pool.enqueue_job(
            "process_event",
            {"event_id": str(event.id), "tenant_id": str(tenant_id)},
        )
        await arq_pool.close()
    except Exception:
        logger.warning("Failed to enqueue process_event job for event %s", event.id)

    return EventResponse.model_validate(event)


@router.post(
    "/batch",
    response_model=list[EventResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_per_minute=60))],
)
async def ingest_event_batch(
    body: EventBatchCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> list[EventResponse]:
    """Ingest a batch of operational events."""
    events: list[Event] = []
    for item in body.events:
        event = Event(
            tenant_id=tenant_id,
            event_type=item.event_type,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            source_system=item.source_system,
            payload=item.payload,
            metadata_=item.metadata,
            occurred_at=item.occurred_at or utc_now(),
        )
        if item.process_id is not None:
            event.process_id = UUID(item.process_id)
        if item.resource_id is not None:
            event.resource_id = UUID(item.resource_id)
        events.append(event)

    db.add_all(events)
    await db.commit()

    for ev in events:
        await db.refresh(ev)

    # Enqueue each event for async processing
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        settings = get_settings()
        arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        for ev in events:
            await arq_pool.enqueue_job(
                "process_event",
                {"event_id": str(ev.id), "tenant_id": str(tenant_id)},
            )
        await arq_pool.close()
    except Exception:
        logger.warning("Failed to enqueue batch process_event jobs")

    return [EventResponse.model_validate(ev) for ev in events]


@router.get(
    "/",
    response_model=PaginatedResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def list_events(
    event_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    source_system: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> PaginatedResponse:
    """List events with optional filters."""
    stmt = sa.select(Event).where(Event.tenant_id == tenant_id)
    count_stmt = sa.select(sa.func.count()).select_from(Event).where(Event.tenant_id == tenant_id)

    if event_type is not None:
        stmt = stmt.where(Event.event_type == event_type)
        count_stmt = count_stmt.where(Event.event_type == event_type)
    if entity_type is not None:
        stmt = stmt.where(Event.entity_type == entity_type)
        count_stmt = count_stmt.where(Event.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Event.entity_id == entity_id)
        count_stmt = count_stmt.where(Event.entity_id == entity_id)
    if source_system is not None:
        stmt = stmt.where(Event.source_system == source_system)
        count_stmt = count_stmt.where(Event.source_system == source_system)
    if from_date is not None:
        stmt = stmt.where(Event.occurred_at >= from_date)
        count_stmt = count_stmt.where(Event.occurred_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Event.occurred_at <= to_date)
        count_stmt = count_stmt.where(Event.occurred_at <= to_date)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(Event.occurred_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return PaginatedResponse(
        items=[EventResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    dependencies=[Depends(RateLimiter(requests_per_minute=300))],
)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant),
) -> EventResponse:
    """Get a single event by ID."""
    stmt = sa.select(Event).where(Event.id == event_id, Event.tenant_id == tenant_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        raise ResourceNotFoundError("Event", str(event_id))

    return EventResponse.model_validate(event)

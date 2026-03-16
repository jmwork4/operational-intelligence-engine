import uuid
from datetime import UTC, datetime


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_trace_id() -> str:
    return uuid.uuid4().hex

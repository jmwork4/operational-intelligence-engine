"""Scheduler configuration loaded from environment variables."""

import os


class SchedulerSettings:
    """Configuration for the OIE scheduler."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://oie:oie@localhost:5432/oie",
    )
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379",
    )
    THRESHOLD_EVAL_INTERVAL_SECONDS: int = int(
        os.getenv("THRESHOLD_EVAL_INTERVAL_SECONDS", "60"),
    )
    COMPOSITE_EVAL_INTERVAL_SECONDS: int = int(
        os.getenv("COMPOSITE_EVAL_INTERVAL_SECONDS", "300"),
    )
    LOCK_CLEANUP_INTERVAL_SECONDS: int = int(
        os.getenv("LOCK_CLEANUP_INTERVAL_SECONDS", "600"),
    )
    EVENT_ARCHIVE_HOUR: int = int(
        os.getenv("EVENT_ARCHIVE_HOUR", "2"),
    )


settings = SchedulerSettings()

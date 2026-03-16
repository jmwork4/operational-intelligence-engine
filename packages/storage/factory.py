"""Factory for obtaining a configured :class:`StorageAdapter` instance.

Usage::

    from packages.storage import get_storage_adapter

    async with get_storage_adapter("minio") as store:
        await store.upload("bucket", "key", data)

When *kwargs* are omitted the factory falls back to environment variables:

* ``OIE_STORAGE_ENDPOINT_URL``
* ``OIE_STORAGE_ACCESS_KEY``
* ``OIE_STORAGE_SECRET_KEY``
* ``OIE_STORAGE_REGION`` (default ``us-east-1``)
"""

from __future__ import annotations

import os

from .adapter import StorageAdapter, StorageError
from .minio import MinIOAdapter
from .s3 import S3Adapter

_PROVIDERS: dict[str, type[StorageAdapter]] = {
    "s3": S3Adapter,
    "minio": MinIOAdapter,
}


def get_storage_adapter(
    provider: str = "s3",
    **kwargs: object,
) -> StorageAdapter:
    """Instantiate a :class:`StorageAdapter` for the given *provider*.

    Parameters
    ----------
    provider:
        ``"s3"`` or ``"minio"``.
    **kwargs:
        Forwarded to the adapter constructor.  When a key is absent the
        corresponding ``OIE_STORAGE_*`` environment variable is used as a
        fallback.

    Returns
    -------
    StorageAdapter
        A concrete adapter instance.  Use it as an async context manager to
        ensure proper cleanup.

    Raises
    ------
    StorageError
        If *provider* is not recognised.
    """
    adapter_cls = _PROVIDERS.get(provider.lower())
    if adapter_cls is None:
        supported = ", ".join(sorted(_PROVIDERS))
        raise StorageError(
            f"Unknown storage provider {provider!r}. "
            f"Supported providers: {supported}"
        )

    # Fall back to environment variables for any missing connection details.
    defaults: dict[str, str | None] = {
        "endpoint_url": os.environ.get("OIE_STORAGE_ENDPOINT_URL"),
        "access_key": os.environ.get("OIE_STORAGE_ACCESS_KEY"),
        "secret_key": os.environ.get("OIE_STORAGE_SECRET_KEY"),
        "region": os.environ.get("OIE_STORAGE_REGION", "us-east-1"),
    }

    merged: dict[str, object] = {
        k: v for k, v in defaults.items() if v is not None
    }
    merged.update(kwargs)

    return adapter_cls(**merged)  # type: ignore[arg-type]

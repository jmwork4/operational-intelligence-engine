"""Object-storage abstraction layer for the Operational Intelligence Engine.

This package provides a vendor-agnostic async interface to S3-compatible
object stores.  Domain code should import only from this package and must
never depend on ``boto3`` or ``aiobotocore`` directly.

Quick start::

    from packages.storage import get_storage_adapter

    async with get_storage_adapter("minio", access_key="admin", secret_key="admin") as store:
        await store.ensure_bucket("oie-data")
        etag = await store.upload("oie-data", "hello.txt", b"world")
        data  = await store.download("oie-data", "hello.txt")
"""

from .adapter import (
    BucketNotFoundError,
    ObjectNotFoundError,
    StorageAdapter,
    StorageError,
    StorageObject,
)
from .factory import get_storage_adapter
from .minio import MinIOAdapter
from .s3 import S3Adapter

__all__ = [
    "BucketNotFoundError",
    "MinIOAdapter",
    "ObjectNotFoundError",
    "S3Adapter",
    "StorageAdapter",
    "StorageError",
    "StorageObject",
    "get_storage_adapter",
]

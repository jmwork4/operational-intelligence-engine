"""Abstract storage adapter interface for the Operational Intelligence Engine.

All object-storage interactions in the OIE must go through a concrete
implementation of :class:`StorageAdapter`.  Domain code must never import
``boto3``, ``aiobotocore``, or any other vendor SDK directly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO


class StorageError(Exception):
    """Base exception for all storage-related errors."""


class BucketNotFoundError(StorageError):
    """Raised when the target bucket does not exist."""


class ObjectNotFoundError(StorageError):
    """Raised when the requested object key does not exist."""


@dataclass(frozen=True, slots=True)
class StorageObject:
    """Lightweight descriptor returned by :meth:`StorageAdapter.list_objects`."""

    key: str
    size: int
    last_modified: datetime
    etag: str


class StorageAdapter(abc.ABC):
    """Asynchronous interface to an S3-compatible object store.

    Concrete subclasses must implement every abstract method below.
    Implementations should be usable as async context managers so that
    underlying sessions/connections are cleaned up properly::

        async with get_storage_adapter("s3") as store:
            await store.upload("my-bucket", "key.bin", data)
    """

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self) -> StorageAdapter:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:  # noqa: B027 – intentionally empty default
        """Release any resources held by the adapter."""

    # -- abstract interface --------------------------------------------------

    @abc.abstractmethod
    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload *data* and return the object's ETag."""

    @abc.abstractmethod
    async def download(self, bucket: str, key: str) -> bytes:
        """Download and return the raw bytes for *key*."""

    @abc.abstractmethod
    async def delete(self, bucket: str, key: str) -> None:
        """Delete *key* from *bucket*.  No-op if the key does not exist."""

    @abc.abstractmethod
    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[StorageObject]:
        """Return all objects whose key starts with *prefix*."""

    @abc.abstractmethod
    async def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned GET URL valid for *expires_in* seconds."""

    @abc.abstractmethod
    async def ensure_bucket(self, bucket: str) -> None:
        """Create *bucket* if it does not already exist."""

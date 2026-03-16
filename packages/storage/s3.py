"""Concrete :class:`StorageAdapter` backed by AWS S3 via *aiobotocore*."""

from __future__ import annotations

import io
import logging
from typing import Any, BinaryIO

from aiobotocore.session import AioSession, get_session
from botocore.exceptions import ClientError

from .adapter import (
    BucketNotFoundError,
    ObjectNotFoundError,
    StorageAdapter,
    StorageError,
    StorageObject,
)

logger = logging.getLogger(__name__)


class S3Adapter(StorageAdapter):
    """S3-compatible storage adapter using *aiobotocore*.

    Usage::

        async with S3Adapter(
            endpoint_url="https://s3.amazonaws.com",
            access_key="AKIA...",
            secret_key="secret",
        ) as s3:
            await s3.upload("my-bucket", "data.json", b'{"ok": true}')
    """

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
        session: AioSession | None = None,
        client_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._session = session or get_session()
        self._client_kwargs: dict[str, Any] = client_kwargs or {}
        self._client_ctx: Any | None = None
        self._client: Any | None = None

    # -- lifecycle -----------------------------------------------------------

    async def _get_client(self) -> Any:
        """Lazily create and cache the S3 client."""
        if self._client is not None:
            return self._client

        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": self._region,
            **self._client_kwargs,
        }
        if self._endpoint_url is not None:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._access_key is not None:
            kwargs["aws_access_key_id"] = self._access_key
        if self._secret_key is not None:
            kwargs["aws_secret_access_key"] = self._secret_key

        self._client_ctx = self._session.create_client(**kwargs)
        self._client = await self._client_ctx.__aenter__()
        return self._client

    async def close(self) -> None:
        """Shut down the underlying *aiobotocore* client."""
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client_ctx = None
            self._client = None

    # -- helpers -------------------------------------------------------------

    def _wrap_error(self, err: ClientError, *, bucket: str, key: str = "") -> StorageError:
        """Translate a botocore ``ClientError`` into a domain exception."""
        code = err.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchBucket", "404") and not key:
            return BucketNotFoundError(f"Bucket not found: {bucket}")
        if code in ("NoSuchKey", "NoSuchObject", "404"):
            return ObjectNotFoundError(
                f"Object not found: s3://{bucket}/{key}"
            )
        return StorageError(f"S3 error ({code}): {err}")

    # -- interface implementation --------------------------------------------

    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        client = await self._get_client()
        body = data if isinstance(data, bytes) else data.read()
        if isinstance(body, str):
            body = body.encode()
        try:
            resp = await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
            )
        except ClientError as exc:
            raise self._wrap_error(exc, bucket=bucket, key=key) from exc

        etag: str = resp.get("ETag", "").strip('"')
        logger.debug("Uploaded s3://%s/%s (etag=%s)", bucket, key, etag)
        return etag

    async def download(self, bucket: str, key: str) -> bytes:
        client = await self._get_client()
        try:
            resp = await client.get_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            raise self._wrap_error(exc, bucket=bucket, key=key) from exc

        async with resp["Body"] as stream:
            data: bytes = await stream.read()
        logger.debug("Downloaded s3://%s/%s (%d bytes)", bucket, key, len(data))
        return data

    async def delete(self, bucket: str, key: str) -> None:
        client = await self._get_client()
        try:
            await client.delete_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            raise self._wrap_error(exc, bucket=bucket, key=key) from exc
        logger.debug("Deleted s3://%s/%s", bucket, key)

    async def list_objects(
        self,
        bucket: str,
        prefix: str = "",
    ) -> list[StorageObject]:
        client = await self._get_client()
        objects: list[StorageObject] = []
        continuation_token: str | None = None

        try:
            while True:
                kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
                if continuation_token is not None:
                    kwargs["ContinuationToken"] = continuation_token

                resp = await client.list_objects_v2(**kwargs)

                for item in resp.get("Contents", []):
                    objects.append(
                        StorageObject(
                            key=item["Key"],
                            size=item["Size"],
                            last_modified=item["LastModified"],
                            etag=item["ETag"].strip('"'),
                        )
                    )

                if resp.get("IsTruncated"):
                    continuation_token = resp.get("NextContinuationToken")
                else:
                    break
        except ClientError as exc:
            raise self._wrap_error(exc, bucket=bucket) from exc

        logger.debug(
            "Listed %d objects in s3://%s/%s", len(objects), bucket, prefix
        )
        return objects

    async def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        client = await self._get_client()
        try:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            raise self._wrap_error(exc, bucket=bucket, key=key) from exc

        logger.debug(
            "Generated presigned URL for s3://%s/%s (expires=%ds)",
            bucket,
            key,
            expires_in,
        )
        return url

    async def ensure_bucket(self, bucket: str) -> None:
        client = await self._get_client()
        try:
            await client.head_bucket(Bucket=bucket)
            logger.debug("Bucket already exists: %s", bucket)
            return
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchBucket"):
                raise self._wrap_error(exc, bucket=bucket) from exc

        try:
            create_kwargs: dict[str, Any] = {"Bucket": bucket}
            if self._region and self._region != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": self._region,
                }
            await client.create_bucket(**create_kwargs)
            logger.info("Created bucket: %s", bucket)
        except ClientError as exc:
            raise self._wrap_error(exc, bucket=bucket) from exc

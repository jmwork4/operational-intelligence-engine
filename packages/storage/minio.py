"""MinIO storage adapter.

MinIO is fully S3-compatible, so :class:`MinIOAdapter` inherits from
:class:`~.s3.S3Adapter` and only adjusts defaults that are specific to a
self-hosted MinIO deployment (path-style addressing, default endpoint, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

from botocore.config import Config as BotocoreConfig

from .s3 import S3Adapter

logger = logging.getLogger(__name__)

_MINIO_DEFAULT_ENDPOINT = "http://localhost:9000"
_MINIO_DEFAULT_REGION = "us-east-1"


class MinIOAdapter(S3Adapter):
    """Storage adapter targeting a MinIO instance.

    By default the adapter connects to ``http://localhost:9000`` with
    path-style addressing enabled, which is the standard MinIO configuration.
    All behaviour is otherwise identical to :class:`S3Adapter`.

    Usage::

        async with MinIOAdapter(
            access_key="minioadmin",
            secret_key="minioadmin",
        ) as minio:
            await minio.ensure_bucket("oie-data")
            await minio.upload("oie-data", "test.txt", b"hello")
    """

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = _MINIO_DEFAULT_REGION,
        client_kwargs: dict[str, Any] | None = None,
    ) -> None:
        merged_kwargs = dict(client_kwargs or {})

        # Force path-style addressing (virtual-host style is not available
        # on a bare MinIO deployment).
        existing_config: BotocoreConfig | None = merged_kwargs.get("config")
        path_style_config = BotocoreConfig(s3={"addressing_style": "path"})
        if existing_config is not None:
            merged_kwargs["config"] = existing_config.merge(path_style_config)
        else:
            merged_kwargs["config"] = path_style_config

        super().__init__(
            endpoint_url=endpoint_url or _MINIO_DEFAULT_ENDPOINT,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            client_kwargs=merged_kwargs,
        )

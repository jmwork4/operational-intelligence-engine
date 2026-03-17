"""OIE Edge Agent — entry point.

Usage::

    python -m apps.edge_agent.main

Configuration is loaded from environment variables or a JSON config file
specified via ``OIE_EDGE_CONFIG`` env var.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

from .agent import EdgeAgent
from .config import EdgeConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oie.edge_agent")


def load_config() -> EdgeConfig:
    """Build an :class:`EdgeConfig` from environment variables or config file."""

    config_path = os.environ.get("OIE_EDGE_CONFIG")
    if config_path and Path(config_path).exists():
        logger.info("Loading config from %s", config_path)
        data = json.loads(Path(config_path).read_text())
        return EdgeConfig(**data)

    # Fall back to individual environment variables
    api_url = os.environ.get("OIE_API_URL", "http://localhost:8000")
    api_key = os.environ.get("OIE_API_KEY", "")
    tenant_id = os.environ.get("OIE_TENANT_ID", "")

    if not api_key:
        logger.warning("OIE_API_KEY not set — sync will fail authentication")
    if not tenant_id:
        logger.warning("OIE_TENANT_ID not set — events will not be associated with a tenant")

    sync_interval = int(os.environ.get("OIE_SYNC_INTERVAL", "30"))
    max_queue = int(os.environ.get("OIE_MAX_QUEUE_SIZE", "10000"))
    storage_path = os.environ.get("OIE_OFFLINE_STORAGE", None)

    # Local rules from env (JSON string)
    local_rules_raw = os.environ.get("OIE_LOCAL_RULES", "[]")
    try:
        local_rules = json.loads(local_rules_raw)
    except json.JSONDecodeError:
        logger.warning("Invalid OIE_LOCAL_RULES JSON — using no local rules")
        local_rules = []

    return EdgeConfig(
        api_url=api_url,
        api_key=api_key,
        tenant_id=tenant_id,
        sync_interval_seconds=sync_interval,
        max_queue_size=max_queue,
        local_rules=local_rules,
        offline_storage_path=storage_path,
    )


async def run() -> None:
    """Create the agent and run until interrupted."""
    config = load_config()
    agent = EdgeAgent(config)

    loop = asyncio.get_running_loop()

    def _shutdown(sig: signal.Signals) -> None:
        logger.info("Received %s — shutting down", sig.name)
        asyncio.ensure_future(agent.stop())

    # Register signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown, sig)

    await agent.start()

    # Keep running until stopped
    try:
        while agent._running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        if agent._running:
            await agent.stop()


def main() -> None:
    """CLI entry point."""
    logger.info("Starting OIE Edge Intelligence Agent")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    logger.info("Edge agent exited")


if __name__ == "__main__":
    main()

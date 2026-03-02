"""
CapiscIO MCP Demo Client — Agent that calls the guarded MCP server.

Demonstrates client-side server verification:
  1. Uses CapiscioMCPClient to connect to the demo server
  2. Client verifies server DID + badge from the _meta in initialize response
  3. Calls tools with different trust levels to show enforcement

Run (after starting the server in another terminal):
    python client/main.py

Environment variables (see ../.env.example):
    CAPISCIO_API_KEY         — Your agent's API key (for badge auth)
    CAPISCIO_AGENT_BADGE     — Agent trust badge (optional, for level ≥1 tools)
    CAPISCIO_SERVER_URL      — Registry URL (default: https://registry.capisc.io)
    CAPISCIO_MIN_TRUST_LEVEL — Minimum trust level to require from server (default: 1)
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

from capiscio_mcp.integrations.mcp import CapiscioMCPClient
from capiscio_mcp.errors import ServerVerifyError


async def run_demo() -> None:
    """Connect to the MCP server and exercise the guarded tools."""

    server_command = os.environ.get("MCP_SERVER_COMMAND", "python")
    server_args = os.environ.get("MCP_SERVER_ARGS", "server/main.py").split()
    agent_badge = os.environ.get("CAPISCIO_AGENT_BADGE")
    min_trust_level = int(os.environ.get("CAPISCIO_MIN_TRUST_LEVEL", "1"))

    logger.info("Connecting to MCP server (command=%s %s)…", server_command, server_args)

    async with CapiscioMCPClient(
        command=server_command,
        args=server_args,
        badge=agent_badge,
        min_trust_level=min_trust_level,
        fail_on_unverified=(min_trust_level > 0),
    ) as client:

        # ── Server identity report ─────────────────────────────────────────
        logger.info("Server DID          : %s", client.server_did or "(not disclosed)")
        logger.info("Server trust level  : %s", client.server_trust_level)
        logger.info("Server state        : %s", client.server_state)

        # ── list_files: open to any caller ────────────────────────────────
        logger.info("\n--- list_files /tmp (min_trust_level=0) ---")
        try:
            result = await client.call_tool("list_files", {"directory": "/tmp"})
            logger.info("Files: %s", result)
        except Exception as exc:
            logger.warning("list_files failed: %s", exc)

        # ── read_file: requires trust level 2 ────────────────────────────
        logger.info("\n--- read_file (min_trust_level=2) ---")
        if agent_badge:
            try:
                result = await client.call_tool(
                    "read_file",
                    {"path": "/tmp/capiscio-demo.txt"},
                )
                logger.info("File content: %s", result)
            except Exception as exc:
                # Expected for lower-trust badges
                logger.info("read_file result: %s", exc)
        else:
            logger.info(
                "No agent badge provided — read_file (trust level 2) will be denied. "
                "Set CAPISCIO_AGENT_BADGE to test with a real badge."
            )

        # ── write_file: requires trust level 3 ───────────────────────────
        logger.info("\n--- write_file (min_trust_level=3) ---")
        logger.info(
            "write_file requires trust level 3 — needs a level-3 badge to succeed."
        )
        if agent_badge:
            try:
                result = await client.call_tool(
                    "write_file",
                    {
                        "path": "/tmp/capiscio-demo.txt",
                        "content": "Hello from CapiscIO MCP demo!\n",
                    },
                )
                logger.info("write_file result: %s", result)
            except Exception as exc:
                logger.info("write_file result: %s", exc)


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()

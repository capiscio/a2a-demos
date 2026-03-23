"""
Demo One — Trusted Agent.

Connects to CapiscIO, obtains a badge, then calls the guarded MCP server.
With a valid badge, this agent can access tools up to its trust level.

This module is imported by run_demo.py — not run directly.
"""

import logging
import os

from capiscio_sdk import CapiscIO, AgentIdentity

logger = logging.getLogger("demo-one.trusted-agent")


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity with a badge."""
    return CapiscIO.connect(
        api_key=os.environ["CAPISCIO_API_KEY"],
        name=os.environ.get("CAPISCIO_TRUSTED_AGENT_NAME", "demo-trusted-agent"),
        server_url=os.environ.get("CAPISCIO_SERVER_URL", "https://dev.registry.capisc.io"),
        auto_badge=True,
    )

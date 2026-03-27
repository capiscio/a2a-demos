"""
Demo One — Untrusted Agent.

Connects to CapiscIO but does NOT obtain a badge.
Without a badge, this agent will be denied access to any tool
requiring trust level > 0.

This module is imported by run_demo.py — not run directly.
"""

import logging
import os

from capiscio_sdk import CapiscIO, AgentIdentity

logger = logging.getLogger("demo-one.untrusted-agent")


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity WITHOUT a badge."""
    return CapiscIO.connect(
        api_key=os.environ["CAPISCIO_API_KEY"],
        name=os.environ.get("CAPISCIO_UNTRUSTED_AGENT_NAME", "demo-untrusted-agent"),
        server_url=os.environ.get("CAPISCIO_SERVER_URL", "https://dev.registry.capisc.io"),
        auto_badge=False,
    )

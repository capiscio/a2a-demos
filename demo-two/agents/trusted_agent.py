"""
Demo Two — Trusted Agent.

Connects to CapiscIO with a badge (auto_badge=True).
With a valid badge (PoP → DV-equivalent), this agent can access tools
up to trust level DV under the baseline policy — but policy changes
can raise or lower the bar.

This module is imported by run_demo.py — not run directly.
"""

import logging
import os

from capiscio_sdk import CapiscIO, AgentIdentity

logger = logging.getLogger("demo-two.trusted-agent")


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity with a badge."""
    return CapiscIO.connect(
        api_key=os.environ["CAPISCIO_API_KEY"],
        name=os.environ.get("CAPISCIO_TRUSTED_AGENT_NAME", "demo-trusted-agent"),
        server_url=os.environ.get("CAPISCIO_SERVER_URL", "https://dev.registry.capisc.io"),
        auto_badge=True,
    )

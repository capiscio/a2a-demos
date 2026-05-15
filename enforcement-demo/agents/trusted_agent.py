"""
Enforcement Demo — Badged Agent.

Connects to CapiscIO, obtains a badge, then calls the guarded MCP server.
With a valid CA-issued badge, this agent can access badge-required tools.

This module is imported by run_demo.py — not run directly.
"""

from pathlib import Path

from capiscio_sdk import CapiscIO, AgentIdentity

KEYS_DIR = Path(__file__).resolve().parent.parent / ".capiscio" / "keys" / "trusted"


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity with a badge."""
    return CapiscIO.connect(name="demo-trusted-agent", keys_dir=KEYS_DIR)

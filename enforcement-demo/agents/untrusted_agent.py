"""
Enforcement Demo — Unbadged Agent.

Connects to CapiscIO but does NOT obtain a badge.
Without a badge, this agent will be denied access to any tool
that requires badge authentication.

This module is imported by run_demo.py — not run directly.
"""

from pathlib import Path

from capiscio_sdk import CapiscIO, AgentIdentity

KEYS_DIR = Path(__file__).resolve().parent.parent / ".capiscio" / "keys"


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity WITHOUT a badge."""
    return CapiscIO.connect(name="demo-untrusted-agent", auto_badge=False, keys_dir=KEYS_DIR)

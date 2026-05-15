"""
Policy Demo — Badged Agent.

Connects to CapiscIO with a badge (auto_badge=True).
With a valid CA-issued badge, this agent can access tools that
require badge authentication under the baseline policy — but
policy changes can raise or lower the bar.

This module is imported by run_demo.py — not run directly.
"""

from pathlib import Path

from capiscio_sdk import CapiscIO, AgentIdentity

KEYS_DIR = Path(__file__).resolve().parent.parent / ".capiscio" / "keys" / "trusted"


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity with a CA-issued badge."""
    return CapiscIO.connect(name="demo-trusted-agent", keys_dir=KEYS_DIR)

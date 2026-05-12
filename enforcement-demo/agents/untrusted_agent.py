"""
Enforcement Demo — Untrusted Agent.

Connects to CapiscIO but does NOT obtain a badge.
Without a badge, this agent will be denied access to any tool
requiring trust level > 0.

This module is imported by run_demo.py — not run directly.
"""

import logging
import os

import httpx

from capiscio_sdk import CapiscIO, AgentIdentity

logger = logging.getLogger("enforcement-demo.untrusted-agent")


def _resolve_agent_id(api_key: str, server_url: str, name: str) -> str | None:
    """Look up agent UUID by name so the SDK uses the correct identity."""
    try:
        resp = httpx.get(
            f"{server_url}/v1/sdk/agents",
            headers={"X-Capiscio-Registry-Key": api_key},
            timeout=10.0,
        )
        if resp.status_code == 200:
            for agent in resp.json().get("data", []):
                if agent.get("name") == name:
                    return agent["id"]
    except Exception:
        pass
    return None


def connect() -> AgentIdentity:
    """Connect to CapiscIO and return an agent identity WITHOUT a badge."""
    api_key = os.environ["CAPISCIO_API_KEY"]
    name = os.environ.get("CAPISCIO_UNTRUSTED_AGENT_NAME", "demo-untrusted-agent")
    server_url = os.environ.get("CAPISCIO_SERVER_URL", "https://registry.capisc.io")
    agent_id = _resolve_agent_id(api_key, server_url, name)
    return CapiscIO.connect(
        api_key=api_key,
        agent_id=agent_id,
        name=name,
        server_url=server_url,
        auto_badge=False,
    )

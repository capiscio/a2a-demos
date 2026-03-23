#!/usr/bin/env python3
"""
Demo One — "Zero to Enforcement"

Runs four scenarios that demonstrate CapiscIO trust enforcement
on an MCP server with three tools at different trust levels:

  Scenario 1: Trusted agent   → get_price    (level 0)  → ALLOW
  Scenario 2: Trusted agent   → place_order  (level 2)  → ALLOW
  Scenario 3: Untrusted agent → get_price    (level 0)  → ALLOW
  Scenario 4: Untrusted agent → place_order  (level 2)  → DENY

The MCP server runs as a subprocess (stdio transport).
Each agent connects to the CapiscIO registry, obtains (or skips) a badge,
then calls the server.  The @guard decorator on the server side enforces
per-tool trust-level requirements.

Usage:
    source .venv/bin/activate
    python run_demo.py

Prerequisites:
    - .env file with CAPISCIO_API_KEY, CAPISCIO_SERVER_ID, CAPISCIO_SERVER_URL
    - Run ./setup.sh first to install deps and pre-download binary
"""

import asyncio
import logging
import os
import sys

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)
# Quiet the noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("capiscio_mcp").setLevel(logging.WARNING)
logging.getLogger("capiscio_sdk").setLevel(logging.WARNING)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from capiscio_mcp.integrations.mcp import CapiscioMCPClient  # noqa: E402

# Add agents/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
import trusted_agent  # noqa: E402
import untrusted_agent  # noqa: E402


# ── Formatting helpers ───────────────────────────────────────────────────

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def banner(text: str) -> None:
    width = 60
    print(f"\n{CYAN}{'═' * width}{RESET}")
    print(f"{CYAN}  {text}{RESET}")
    print(f"{CYAN}{'═' * width}{RESET}\n")


def scenario_header(num: int, agent_type: str, tool: str, level: int, expected: str) -> None:
    color = GREEN if expected == "ALLOW" else RED
    print(f"\n{BOLD}── Scenario {num} ──────────────────────────────────────────{RESET}")
    print(f"  Agent : {agent_type}")
    print(f"  Tool  : {tool} (min_trust_level={level})")
    print(f"  Expect: {color}{expected}{RESET}")
    print()


def result_line(outcome: str, detail: str) -> None:
    color = GREEN if outcome == "ALLOW" else RED
    print(f"  Result: {color}{BOLD}{outcome}{RESET} — {detail}")


# ── Scenario runner ──────────────────────────────────────────────────────


async def call_tool(badge: str | None, tool_name: str, args: dict) -> tuple[str, str]:
    """
    Spawn the MCP server, call one tool, return (outcome, detail).

    The server is started as a subprocess each time — this is intentional
    for demo clarity.  In production you'd keep the connection alive.
    """
    server_cmd = sys.executable
    server_args = [os.path.join(os.path.dirname(__file__), "server", "main.py")]

    try:
        async with CapiscioMCPClient(
            command=server_cmd,
            args=server_args,
            badge=badge,
            min_trust_level=0,
            fail_on_unverified=False,
        ) as client:
            result = await client.call_tool(tool_name, args)

            # Result may be a list of TextContent or a string
            if isinstance(result, list):
                text = " ".join(
                    getattr(item, "text", str(item)) for item in result
                )
            else:
                text = str(result)

            # Check if the result indicates a guard denial
            lower = text.lower()
            if "denied" in lower or "insufficient" in lower or "trust" in lower:
                return ("DENY", text)
            return ("ALLOW", text)

    except Exception as exc:
        msg = str(exc)
        if "denied" in msg.lower() or "guard" in msg.lower() or "trust" in msg.lower():
            return ("DENY", msg)
        return ("ERROR", msg)


async def run_demo() -> None:
    banner("CapiscIO Demo One — Zero to Enforcement")

    # ── Connect agents ───────────────────────────────────────────────
    print(f"{BOLD}Connecting agents to CapiscIO registry...{RESET}")
    print(f"  Server URL: {os.environ.get('CAPISCIO_SERVER_URL', 'https://dev.registry.capisc.io')}")
    print()

    print("  Connecting trusted agent (with badge)...")
    trusted = trusted_agent.connect()
    print(f"    DID  : {trusted.did}")
    trusted_badge = trusted.get_badge()
    print(f"    Badge: {'✓ obtained' if trusted_badge else '✗ none'}")
    print()

    print("  Connecting untrusted agent (no badge)...")
    untrusted = untrusted_agent.connect()
    print(f"    DID  : {untrusted.did}")
    untrusted_badge = untrusted.get_badge()
    print(f"    Badge: {'✓ obtained' if untrusted_badge else '✗ none (as expected)'}")

    # ── Scenarios ────────────────────────────────────────────────────
    banner("Running Enforcement Scenarios")

    # Scenario 1: Trusted agent → open tool → ALLOW
    scenario_header(1, "trusted (badged)", "get_price", 0, "ALLOW")
    outcome, detail = await call_tool(trusted_badge, "get_price", {"sku": "WIDGET-A"})
    result_line(outcome, detail)

    # Scenario 2: Trusted agent → restricted tool → ALLOW
    scenario_header(2, "trusted (badged)", "place_order", 2, "ALLOW")
    outcome, detail = await call_tool(
        trusted_badge, "place_order", {"sku": "WIDGET-B", "quantity": 3}
    )
    result_line(outcome, detail)

    # Scenario 3: Untrusted agent → open tool → ALLOW
    scenario_header(3, "untrusted (no badge)", "get_price", 0, "ALLOW")
    outcome, detail = await call_tool(untrusted_badge, "get_price", {"sku": "WIDGET-C"})
    result_line(outcome, detail)

    # Scenario 4: Untrusted agent → restricted tool → DENY
    scenario_header(4, "untrusted (no badge)", "place_order", 2, "DENY")
    outcome, detail = await call_tool(
        untrusted_badge, "place_order", {"sku": "WIDGET-A", "quantity": 1}
    )
    result_line(outcome, detail)

    # ── Summary ──────────────────────────────────────────────────────
    banner("Summary")
    print("  The @guard decorator on the MCP server enforced per-tool")
    print("  trust-level requirements.  The trusted agent's badge gave it")
    print("  access to place_order (level 2), while the untrusted agent")
    print("  was denied — even though it could still call get_price (level 0).")
    print()
    print(f"  View events in the dashboard: {CYAN}https://dev.app.capisc.io{RESET}")
    print()

    # Clean up
    trusted.close()
    untrusted.close()


def main() -> None:
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()

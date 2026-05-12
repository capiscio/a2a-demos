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
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("capiscio_mcp").setLevel(logging.WARNING)
logging.getLogger("capiscio_sdk").setLevel(logging.WARNING)

from capiscio_mcp.integrations.mcp import CapiscioMCPClient  # noqa: E402


# ── Formatting helpers ───────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
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


def scenario_header(num: int, tool: str, level: int, badge_status: str, expected: str) -> None:
    color = GREEN if expected == "ALLOW" else RED
    print(f"\n{BOLD}── Scenario {num} ──────────────────────────────────────────{RESET}")
    print(f"  Tool  : {tool} (min_trust_level={level})")
    print(f"  Badge : {badge_status}")
    print(f"  Expect: {color}{expected}{RESET}")
    print()


def result_line(outcome: str, detail: str) -> None:
    color = GREEN if outcome == "ALLOW" else RED
    print(f"  Result: {color}{BOLD}{outcome}{RESET} — {detail}")


def pause(hint: str = "") -> None:
    """Wait for the presenter to press Enter before continuing."""
    msg = f"\n  {YELLOW}▸ Press Enter to continue{RESET}"
    if hint:
        msg += f"  {YELLOW}({hint}){RESET}"
    input(msg + " ")
    print()


async def run_demo() -> None:
    """Connect to the MCP server and exercise the guarded tools."""

    server_command = os.environ.get("MCP_SERVER_COMMAND", "python")
    server_args = os.environ.get("MCP_SERVER_ARGS", "server/main.py").split()
    agent_badge = os.environ.get("CAPISCIO_AGENT_BADGE")
    min_trust_level = int(os.environ.get("CAPISCIO_MIN_TRUST_LEVEL", "1"))

    banner("CapiscIO MCP Demo — Server Identity & Client Verification")

    print(f"{BOLD}Connecting to MCP server...{RESET}")
    print(f"  Command: {server_command} {' '.join(server_args)}")
    print()

    async with CapiscioMCPClient(
        command=server_command,
        args=server_args,
        badge=agent_badge,
        min_trust_level=min_trust_level,
        fail_on_unverified=(min_trust_level > 0),
    ) as client:

        # ── Server identity report ─────────────────────────────────────
        banner("Server Identity Verification")
        server_did = client.server_did or "(not disclosed)"
        trust_level = client.server_trust_level
        state = client.server_state

        state_color = GREEN if "VERIFIED" in str(state).upper() else RED
        print(f"  Server DID          : {CYAN}{server_did}{RESET}")
        print(f"  Server trust level  : {BOLD}{trust_level}{RESET}")
        print(f"  Server state        : {state_color}{BOLD}{state}{RESET}")
        print()
        print(f"  {DIM}The client verified the server's DID + badge from the{RESET}")
        print(f"  {DIM}initialize response _meta (RFC-007).{RESET}")

        badge_label = "agent badge (level unknown)" if agent_badge else "none"

        pause("next: call an open tool (list_files)")

        # ── Scenario 1: list_files — open to any caller ────────────────
        scenario_header(1, "list_files", 0, badge_label, "ALLOW")
        try:
            result = await client.call_tool("list_files", {"directory": "."})
            if isinstance(result, list):
                text = " ".join(getattr(item, "text", str(item)) for item in result)
            elif hasattr(result, "content"):
                text = " ".join(getattr(item, "text", str(item)) for item in result.content)
            else:
                text = str(result)
            result_line("ALLOW", text[:120] + ("…" if len(text) > 120 else ""))
        except Exception as exc:
            result_line("ERROR", str(exc))

        pause("next: call a restricted tool (read_file, level 2)")

        # ── Scenario 2: read_file — requires trust level 2 ────────────
        expected = "ALLOW" if agent_badge else "DENY"
        scenario_header(2, "read_file", 2, badge_label, expected)
        if agent_badge:
            try:
                result = await client.call_tool("read_file", {"path": "test.txt"})
                if isinstance(result, list):
                    text = " ".join(getattr(item, "text", str(item)) for item in result)
                elif hasattr(result, "content"):
                    text = " ".join(getattr(item, "text", str(item)) for item in result.content)
                else:
                    text = str(result)
                lower = text.lower()
                if any(kw in lower for kw in ("denied", "badge_missing", "badge_invalid", "trust")):
                    result_line("DENY", text)
                else:
                    result_line("ALLOW", text)
            except Exception as exc:
                result_line("DENY", str(exc))
        else:
            print(f"  {DIM}No agent badge — skipping call (would be denied).{RESET}")
            print(f"  {DIM}Set CAPISCIO_AGENT_BADGE to test with a real badge.{RESET}")
            result_line("DENY", "badge_missing: no agent badge provided")

        pause("next: call a high-trust tool (write_file, level 3)")

        # ── Scenario 3: write_file — requires trust level 3 ───────────
        scenario_header(3, "write_file", 3, badge_label, "DENY")
        if agent_badge:
            try:
                result = await client.call_tool(
                    "write_file",
                    {"path": "test.txt", "content": "Hello from CapiscIO!\n"},
                )
                if isinstance(result, list):
                    text = " ".join(getattr(item, "text", str(item)) for item in result)
                elif hasattr(result, "content"):
                    text = " ".join(getattr(item, "text", str(item)) for item in result.content)
                else:
                    text = str(result)
                lower = text.lower()
                if any(kw in lower for kw in ("denied", "badge_missing", "badge_invalid", "trust")):
                    result_line("DENY", text)
                else:
                    result_line("ALLOW", text)
            except Exception as exc:
                result_line("DENY", str(exc))
        else:
            print(f"  {DIM}No agent badge — skipping call (would be denied).{RESET}")
            result_line("DENY", "badge_missing: no agent badge provided")

        pause("show summary")

        # ── Summary ────────────────────────────────────────────────────
        banner("Summary")
        print("  The MCP server obtained its identity automatically via")
        print("  MCPServerIdentity.from_env() — one line of code.")
        print()
        print("  The client verified the server's DID and badge from the")
        print("  initialize response before calling any tools.")
        print()
        print(f"  {BOLD}Bidirectional trust:{RESET}")
        print("    Servers prove identity to clients (RFC-007)")
        print("    Clients prove trust to servers via badges (RFC-006)")
        print("    Both are cryptographically verified — no config flags")
        print()
        print(f"  View events: {CYAN}https://app.capisc.io{RESET}")
        print()

    # Clean up
    logging.getLogger("capiscio_sdk.badge_keeper").setLevel(logging.CRITICAL)


def main() -> None:
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()

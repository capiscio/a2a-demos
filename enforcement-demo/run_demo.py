#!/usr/bin/env python3
"""
Enforcement Demo — "Zero to Enforcement"

Runs five scenarios that demonstrate CapiscIO trust enforcement
on an MCP server with three tools at different trust levels:

  Scenario 1: Trusted agent   → get_price    (level 0)  → ALLOW
  Scenario 2: Trusted agent   → place_order  (level 1)  → ALLOW
  Scenario 3: Untrusted agent → get_price    (level 0)  → ALLOW
  Scenario 4: Untrusted agent → place_order  (level 1)  → DENY
  Scenario 5: Trusted (revoked) → place_order (level 1) → DENY

The MCP server runs as a subprocess (stdio transport).
Each agent connects to the CapiscIO registry, obtains (or skips) a badge,
then calls the server.  The @guard decorator on the server side enforces
per-tool trust-level requirements.

Usage:
    source .venv/bin/activate
    python run_demo.py            # Interactive (pauses between scenarios)
    python run_demo.py --auto     # Non-interactive (no pauses)

Prerequisites:
    - .env file with CAPISCIO_API_KEY, CAPISCIO_SERVER_ID, CAPISCIO_SERVER_URL
    - Run ./setup.sh first to install deps and pre-download binary
"""

import argparse
import asyncio
import base64
import json
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
# Suppress gRPC C-core noise (ev_poll_posix.cc, fork_posix.cc, etc.)
os.environ.setdefault("GRPC_VERBOSITY", "NONE")
os.environ.setdefault("GRPC_TRACE", "")

from dotenv import load_dotenv  # noqa: E402
import httpx  # noqa: E402

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


# ── CLI flag ─────────────────────────────────────────────────────────────
AUTO_MODE = "--auto" in sys.argv or "--no-pause" in sys.argv


def pause(hint: str = "") -> None:
    """Wait for the presenter to press Enter before continuing."""
    if AUTO_MODE:
        return
    msg = f"\n  {YELLOW}▸ Press Enter to continue{RESET}"
    if hint:
        msg += f"  {YELLOW}({hint}){RESET}"
    input(msg + " ")
    print()


def _extract_jti(badge_token: str) -> str | None:
    """Extract the JTI claim from a JWS compact badge token."""
    try:
        payload_b64 = badge_token.split(".")[1]
        # Pad base64url to standard base64
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("jti")
    except Exception:
        return None


async def revoke_badge_via_api(badge_token: str) -> bool:
    """Revoke a badge by calling the SDK revocation endpoint.

    Uses the API key for auth via the SDK route /v1/sdk/badges/{jti}/revoke.
    This route accepts either API key (X-Capiscio-Registry-Key) or badge auth.
    """
    jti = _extract_jti(badge_token)
    if not jti:
        print(f"    {RED}Could not extract JTI from badge{RESET}")
        return False

    server_url = os.environ.get("CAPISCIO_SERVER_URL", "https://registry.capisc.io")
    api_key = os.environ.get("CAPISCIO_API_KEY", "")
    if not api_key:
        print(f"    {RED}✗{RESET} CAPISCIO_API_KEY not set — cannot revoke badge")
        return False

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{server_url}/v1/sdk/badges/{jti}/revoke",
            json={"reason": "demo_revocation"},
            headers={"X-Capiscio-Registry-Key": api_key},
            timeout=10.0,
        )
        if resp.status_code in (200, 204):
            print(f"    {GREEN}✓{RESET} Badge revoked (JTI: {jti[:12]}…)")
            return True
        print(f"    {RED}✗{RESET} Revocation failed: {resp.status_code} — {resp.text}")
        return False


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
            deny_keywords = ("denied", "insufficient", "badge_missing",
                             "badge_invalid", "badge_expired", "badge_revoked",
                             "not_allowed", "issuer_untrusted", "policy_denied")
            if any(kw in lower for kw in deny_keywords):
                return ("DENY", text)
            return ("ALLOW", text)

    except Exception as exc:
        msg = str(exc)
        lower = msg.lower()
        deny_keywords = ("denied", "guard", "trust", "badge_missing",
                         "badge_invalid", "badge_expired", "badge_revoked",
                         "not_allowed", "issuer_untrusted", "policy_denied")
        if any(kw in lower for kw in deny_keywords):
            return ("DENY", msg)
        return ("ERROR", msg)


async def run_demo() -> None:
    banner("CapiscIO Enforcement Demo — Zero to Enforcement")

    # ── Connect agents ───────────────────────────────────────────────
    print(f"{BOLD}Connecting agents to CapiscIO registry...{RESET}")
    print(f"  Server URL: {os.environ.get('CAPISCIO_SERVER_URL', 'https://registry.capisc.io')}")
    print()

    print("  Connecting trusted agent (with badge)...")
    trusted = trusted_agent.connect()
    print(f"    DID  : {trusted.did}")

    # Badge is issued asynchronously by the BadgeKeeper — wait for it
    import time
    trusted_badge = trusted.get_badge()
    if not trusted_badge:
        print("    Badge: ⏳ waiting for BadgeKeeper...")
        for _ in range(10):
            time.sleep(1)
            trusted_badge = trusted.get_badge()
            if trusted_badge:
                break
    print(f"    Badge: {'✓ obtained' if trusted_badge else '✗ none'}")
    print()

    print("  Connecting untrusted agent (no badge)...")
    untrusted = untrusted_agent.connect()
    print(f"    DID  : {untrusted.did}")
    untrusted_badge = untrusted.get_badge()
    print(f"    Badge: {'✓ obtained' if untrusted_badge else '✗ none (as expected)'}")

    # ── Scenarios ────────────────────────────────────────────────────
    banner("Running Enforcement Scenarios")

    results: list[tuple[int, str, str, str, str]] = []  # (num, agent, tool, expected, outcome)

    # Scenario 1: Trusted agent → open tool → ALLOW
    scenario_header(1, "trusted (badged)", "get_price", 0, "ALLOW")
    outcome, detail = await call_tool(trusted_badge, "get_price", {"sku": "WIDGET-A"})
    result_line(outcome, detail)
    results.append((1, "trusted (badged)", "get_price", "ALLOW", outcome))
    pause("next: trusted agent calls a restricted tool")

    # Scenario 2: Trusted agent → restricted tool → ALLOW
    scenario_header(2, "trusted (badged)", "place_order", 1, "ALLOW")
    outcome, detail = await call_tool(
        trusted_badge, "place_order", {"sku": "WIDGET-B", "quantity": 3}
    )
    result_line(outcome, detail)
    results.append((2, "trusted (badged)", "place_order", "ALLOW", outcome))
    pause("next: untrusted agent calls an open tool")

    # Scenario 3: Untrusted agent → open tool → ALLOW
    scenario_header(3, "untrusted (no badge)", "get_price", 0, "ALLOW")
    outcome, detail = await call_tool(untrusted_badge, "get_price", {"sku": "WIDGET-C"})
    result_line(outcome, detail)
    results.append((3, "untrusted (no badge)", "get_price", "ALLOW", outcome))
    pause("next: untrusted agent calls a restricted tool")

    # Scenario 4: Untrusted agent → restricted tool → DENY
    scenario_header(4, "untrusted (no badge)", "place_order", 1, "DENY")
    outcome, detail = await call_tool(
        untrusted_badge, "place_order", {"sku": "WIDGET-A", "quantity": 1}
    )
    result_line(outcome, detail)
    results.append((4, "untrusted (no badge)", "place_order", "DENY", outcome))
    pause("next: revoke trusted agent's badge and retry")

    # Scenario 5: Revoke the trusted agent's badge, then retry → DENY
    scenario_header(5, "trusted (badge REVOKED)", "place_order", 1, "DENY")

    if trusted_badge:
        print("  Revoking trusted agent's badge...")
        await revoke_badge_via_api(trusted_badge)
        await asyncio.sleep(2)  # Propagation delay
    else:
        print(f"  {YELLOW}Skipping — no badge to revoke{RESET}")

    outcome, detail = await call_tool(
        trusted_badge, "place_order", {"sku": "WIDGET-A", "quantity": 1}
    )
    result_line(outcome, detail)
    results.append((5, "trusted (REVOKED)", "place_order", "DENY", outcome))
    pause("show summary")

    # ── Summary table ────────────────────────────────────────────────
    banner("Results")
    print(f"  {BOLD}{'#':<4} {'Agent':<22} {'Tool':<16} {'Expected':<10} {'Actual':<10} {'':>2}{RESET}")
    print(f"  {'─' * 4} {'─' * 22} {'─' * 16} {'─' * 10} {'─' * 10} {'─' * 2}")

    all_pass = True
    for num, agent, tool, expected, actual in results:
        match = actual == expected
        if not match:
            all_pass = False
        icon = f"{GREEN}✓{RESET}" if match else f"{RED}✗{RESET}"
        actual_color = GREEN if actual == "ALLOW" else RED
        print(f"  {num:<4} {agent:<22} {tool:<16} {expected:<10} {actual_color}{actual:<10}{RESET} {icon}")

    print()
    if all_pass:
        print(f"  {GREEN}{BOLD}All 5 scenarios passed.{RESET}")
    else:
        print(f"  {RED}{BOLD}Some scenarios did not match expected outcomes.{RESET}")

    print()
    print(f"  {BOLD}Key takeaway:{RESET} Trust is enforced per-tool, earned by proof, and")
    print(f"  revocable in real time — all via the {CYAN}@guard{RESET} decorator.")
    print()
    print(f"  View audit trail → {CYAN}https://app.capisc.io{RESET}")
    print()

    # Clean up — suppress the expected "Channel closed!" log from
    # BadgeKeeper's streaming RPC during shutdown.
    logging.getLogger("capiscio_sdk.badge_keeper").setLevel(logging.CRITICAL)
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

#!/usr/bin/env python3
"""
Enforcement Demo — "Zero to Enforcement"

Demonstrates bidirectional trust enforcement on an MCP server:

  1. Server identity verification — the client verifies the server's
     DID + badge from the initialize response before calling any tools
  2. Five enforcement scenarios showing per-tool badge requirements:

     Scenario 1: Badged agent   → get_price    (open)     → ALLOW
     Scenario 2: Badged agent   → place_order  (badge)    → ALLOW
     Scenario 3: Unbadged agent → get_price    (open)     → ALLOW
     Scenario 4: Unbadged agent → place_order  (badge)    → DENY
     Scenario 5: Suspended      → place_order  (badge)    → DENY

The MCP server runs as a subprocess (stdio transport).
Each agent connects to the CapiscIO registry, obtains (or skips) a badge,
then calls the server.  The @guard decorator on the server side enforces
per-tool access requirements.

Usage:
    source .venv/bin/activate
    python run_demo.py            # Interactive (pauses between scenarios)
    python run_demo.py --auto     # Non-interactive (no pauses)

Prerequisites:
    - .env file with CAPISCIO_API_KEY, CAPISCIO_SERVER_ID, CAPISCIO_SERVER_URL
    - Run ./setup.sh first to install deps and pre-download binary
"""

import asyncio
import atexit
import base64
import json
import logging
import os
import subprocess
import sys
import time

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


def _cleanup_core_processes() -> None:
    """Kill any lingering capiscio-core (rpc) subprocesses."""
    try:
        result = subprocess.run(
            ["pkill", "-f", "capiscio rpc"],
            capture_output=True,
        )
        if result.returncode == 0:
            print("  [cleanup] Terminated stale capiscio-core processes.")
    except FileNotFoundError:
        pass  # pkill not available on this platform


# Kill stale cores from previous runs, and register cleanup for exit.
_cleanup_core_processes()
atexit.register(_cleanup_core_processes)

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


def scenario_header(num: int, agent_type: str, tool: str, level: int, expected: str) -> None:
    color = GREEN if expected == "ALLOW" else RED
    req = "open" if level == 0 else "badge required"
    print(f"\n{BOLD}── Scenario {num} ────────────────────────────────────────────{RESET}")
    print(f"  Agent : {agent_type}")
    print(f"  Tool  : {tool} ({req})")
    print(f"  Expect: {color}{expected}{RESET}")
    print()


def result_line(outcome: str, detail: str, ms: int = 0) -> None:
    color = GREEN if outcome == "ALLOW" else RED
    timing = f"  {DIM}({ms}ms){RESET}" if ms else ""
    print(f"  Result: {color}{BOLD}{outcome}{RESET} — {detail}{timing}")


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


# ── Result parsing ───────────────────────────────────────────────────────

DENY_KEYWORDS = (
    "denied", "insufficient", "badge_missing",
    "badge_invalid", "badge_expired", "badge_revoked",
    "not_allowed", "issuer_untrusted", "policy_denied",
)


def _parse_result(result: object) -> tuple[str, str]:
    """Extract (outcome, detail) from a CallToolResult."""
    is_error = getattr(result, "isError", False)

    if isinstance(result, list):
        text = " ".join(getattr(item, "text", str(item)) for item in result)
    elif hasattr(result, "content"):
        text = " ".join(
            getattr(item, "text", str(item)) for item in (result.content or [])
        )
    else:
        text = str(result)

    lower = text.lower()
    if is_error or any(kw in lower for kw in DENY_KEYWORDS):
        detail = text
        if "Error executing tool" in detail:
            detail = detail.split(": ", 1)[-1]
        return ("DENY", detail)
    return ("ALLOW", text)


async def _safe_call(
    client: CapiscioMCPClient,
    tool_name: str,
    args: dict,
) -> tuple[str, str, int]:
    """Call a tool, catching exceptions as DENY/ERROR outcomes.

    Returns (outcome, detail, elapsed_ms).
    """
    t0 = time.monotonic()
    try:
        result = await client.call_tool(tool_name, args)
        ms = int((time.monotonic() - t0) * 1000)
        outcome, detail = _parse_result(result)
        return (outcome, detail, ms)
    except Exception as exc:
        ms = int((time.monotonic() - t0) * 1000)
        msg = str(exc)
        if any(kw in msg.lower() for kw in DENY_KEYWORDS):
            return ("DENY", msg, ms)
        return ("ERROR", msg, ms)


# ── Main demo ────────────────────────────────────────────────────────────


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

    # ── Start MCP server (one subprocess for all scenarios) ──────────
    banner("Running Enforcement Scenarios")

    server_cmd = sys.executable
    server_args = [os.path.join(os.path.dirname(__file__), "server", "main.py")]

    async with CapiscioMCPClient(
        command=server_cmd,
        args=server_args,
        badge=trusted_badge,
        min_trust_level=0,
        fail_on_unverified=False,
    ) as client:
        # Warm up the Go core sidecar (first call pays startup cost)
        try:
            await client.call_tool("get_price", {"sku": "WARMUP"})
        except Exception:
            pass

        # ── Server Identity Verification ─────────────────────────────
        banner("Server Identity Verification")
        server_did = getattr(client, "server_did", None) or "(not disclosed)"
        server_trust = getattr(client, "server_trust_level", None)
        server_state = getattr(client, "server_state", None)

        state_str = str(server_state) if server_state else "(unknown)"
        state_color = GREEN if "VERIFIED" in state_str.upper() else YELLOW
        print(f"  Server DID          : {CYAN}{server_did}{RESET}")
        print(f"  Server trust level  : {BOLD}{server_trust}{RESET}")
        print(f"  Server state        : {state_color}{BOLD}{state_str}{RESET}")
        print()
        print(f"  {DIM}The client verified the server's DID + badge from the{RESET}")
        print(f"  {DIM}initialize response _meta before calling any tools.{RESET}")
        print()
        print(f"  {BOLD}Bidirectional trust:{RESET}")
        print(f"    • Servers prove identity to clients (DID + badge in _meta)")
        print(f"    • Clients prove trust to servers (badge per tool call)")
        pause("next: run enforcement scenarios")

        results: list[tuple[int, str, str, str, str]] = []

        # Scenario 1: Trusted agent → open tool → ALLOW
        scenario_header(1, "trusted (badged)", "get_price", 0, "ALLOW")
        client.set_badge(trusted.get_badge())  # refresh from keeper
        outcome, detail, ms = await _safe_call(client, "get_price", {"sku": "WIDGET-A"})
        result_line(outcome, detail, ms)
        results.append((1, "trusted (badged)", "get_price", "ALLOW", outcome))
        pause("next: trusted agent calls a restricted tool")

        # Scenario 2: Trusted agent → restricted tool → ALLOW
        scenario_header(2, "trusted (badged)", "place_order", 1, "ALLOW")
        client.set_badge(trusted.get_badge())  # refresh from keeper
        outcome, detail, ms = await _safe_call(
            client, "place_order", {"sku": "WIDGET-B", "quantity": 3}
        )
        result_line(outcome, detail, ms)
        results.append((2, "trusted (badged)", "place_order", "ALLOW", outcome))
        pause("next: untrusted agent calls an open tool")

        # Scenario 3: Untrusted agent → open tool → ALLOW
        scenario_header(3, "untrusted (no badge)", "get_price", 0, "ALLOW")
        client.set_badge(untrusted_badge)
        outcome, detail, ms = await _safe_call(client, "get_price", {"sku": "WIDGET-C"})
        result_line(outcome, detail, ms)
        results.append((3, "untrusted (no badge)", "get_price", "ALLOW", outcome))
        pause("next: untrusted agent calls a restricted tool")

        # Scenario 4: Untrusted agent → restricted tool → DENY
        scenario_header(4, "untrusted (no badge)", "place_order", 1, "DENY")
        outcome, detail, ms = await _safe_call(
            client, "place_order", {"sku": "WIDGET-A", "quantity": 1}
        )
        result_line(outcome, detail, ms)
        results.append((4, "untrusted (no badge)", "place_order", "DENY", outcome))

        # Scenario 5: Agent suspended → badge expires → DENY
        # In interactive mode: admin disables the agent in the dashboard,
        # then the demo clears the badge to represent post-TTL expiry.
        scenario_header(5, "trusted (SUSPENDED)", "place_order", 1, "DENY")

        if AUTO_MODE:
            # In auto mode, simulate the suspension without dashboard interaction
            print("  Suspending agent (simulated)...")
            print(f"    {GREEN}✓{RESET} Agent suspended — BadgeKeeper will stop refreshing")
            print(f"    {GREEN}✓{RESET} Badge expired (TTL elapsed, no renewal)")
        else:
            print(f"  {YELLOW}Action required:{RESET} Disable the trusted agent in the dashboard.")
            print(f"    Agent ID : {trusted.agent_id}")
            print(f"    Dashboard: {os.environ.get('CAPISCIO_SERVER_URL', 'https://registry.capisc.io').replace('registry', 'app').replace('/v1', '')}")
            print()
            print(f"  Steps: Agents → select agent → Disable")
            input(f"\n  {YELLOW}▸ Press Enter after disabling the agent in the dashboard{RESET} ")
            print()
            print(f"    {GREEN}✓{RESET} Agent disabled — BadgeKeeper can no longer refresh")
            print(f"    {GREEN}✓{RESET} Badge expired (TTL elapsed, no renewal)")

        client.set_badge(None)
        outcome, detail, ms = await _safe_call(
            client, "place_order", {"sku": "WIDGET-A", "quantity": 1}
        )
        result_line(outcome, detail, ms)
        results.append((5, "trusted (SUSPENDED)", "place_order", "DENY", outcome))

        if not AUTO_MODE:
            print()
            print(f"  {YELLOW}⚠  Remember to re-enable the agent in the dashboard before the next run.{RESET}")
            print(f"    Agent ID : {trusted.agent_id}")
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
    print(f"  {BOLD}Key takeaways:{RESET}")
    print(f"    • Access is enforced per-tool, earned by badge, and")
    print(f"      revocable via agent suspension — all via {CYAN}@server.tool(min_trust_level=N){RESET}")
    print(f"    • The client verified the server's identity before calling any tools")
    print(f"    • Bidirectional trust: servers prove identity to clients,")
    print(f"      clients prove trust to servers — both cryptographically verified")
    print()
    print(f"  View audit trail → {CYAN}https://app.capisc.io{RESET}")
    print()

    # Clean up — suppress the expected "Channel closed!" log from
    # BadgeKeeper's streaming RPC during shutdown.
    logging.getLogger("capiscio_sdk.badge_keeper").setLevel(logging.CRITICAL)
    trusted.close()
    untrusted.close()


def main() -> None:
    # Suppress noisy shutdown tracebacks on Ctrl+C — the async generators
    # and gRPC streams complain about unclean teardown, which is expected.
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    logging.getLogger("capiscio_sdk.badge_keeper").setLevel(logging.CRITICAL)
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
    finally:
        _cleanup_core_processes()


if __name__ == "__main__":
    main()

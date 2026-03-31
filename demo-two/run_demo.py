#!/usr/bin/env python3
"""
Demo Two — "Policy as Code"

Shows how org-level policy changes alter enforcement at runtime
WITHOUT any code changes or redeployments.  The same MCP server and
agents produce different ALLOW/DENY outcomes depending on which
policy the admin has activated.

Three phases (presenter switches policies in the dashboard between them):

  Phase 1 — Baseline
    Default enforcement.  Trust levels as coded in @guard decorators.
    Trusted (DV) can call get_price and place_order.
    Untrusted can only call get_price.

  Phase 2 — Lockdown
    Global min_trust_level raised to EV.
    ALL agents (including trusted DV) are denied everything.

  Phase 3 — Selective
    get_price overridden to require DV — a "public" tool becomes
    restricted without any code change.  Trusted still works;
    untrusted is now denied even get_price.

Usage:
    source .venv/bin/activate
    python run_demo.py

Prerequisites:
    - .env file with credentials
    - Run scripts/setup_policies.py first to create the three policies
    - Baseline policy must be the initial active policy
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
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("capiscio_mcp").setLevel(logging.WARNING)
logging.getLogger("capiscio_sdk").setLevel(logging.WARNING)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from capiscio_mcp.integrations.mcp import CapiscioMCPClient  # noqa: E402

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
MAGENTA = "\033[95m"
RESET = "\033[0m"


def banner(text: str) -> None:
    width = 60
    print(f"\n{CYAN}{'═' * width}{RESET}")
    print(f"{CYAN}  {text}{RESET}")
    print(f"{CYAN}{'═' * width}{RESET}\n")


def phase_header(num: int, name: str, policy: str, description: str) -> None:
    print(f"\n{MAGENTA}{'━' * 60}{RESET}")
    print(f"{MAGENTA}{BOLD}  Phase {num}: {name}{RESET}")
    print(f"  Policy  : {YELLOW}{policy}{RESET}")
    print(f"  Effect  : {description}")
    print(f"{MAGENTA}{'━' * 60}{RESET}")


def scenario_header(num: int, agent_type: str, tool: str, expected: str) -> None:
    color = GREEN if expected == "ALLOW" else RED
    print(f"\n  {BOLD}Scenario {num}{RESET}: {agent_type} → {tool} → {color}{expected}{RESET}")


def result_line(outcome: str, detail: str) -> None:
    color = GREEN if outcome == "ALLOW" else RED
    symbol = "✓" if outcome == "ALLOW" else "✗"
    print(f"    {color}{symbol} {outcome}{RESET} — {detail}")


def policy_table(rows: list[tuple[str, str, str, str]]) -> None:
    """Print expected outcomes table for a phase."""
    print(f"\n  {DIM}{'Agent':<22} {'Tool':<18} {'Expected':<8}{RESET}")
    print(f"  {DIM}{'─' * 22} {'─' * 18} {'─' * 8}{RESET}")
    for agent, tool, expected, reason in rows:
        color = GREEN if expected == "ALLOW" else RED
        print(f"  {agent:<22} {tool:<18} {color}{expected:<8}{RESET} {DIM}{reason}{RESET}")


# ── Tool caller ──────────────────────────────────────────────────────────


async def call_tool(badge: str | None, tool_name: str, args: dict) -> tuple[str, str]:
    """Spawn the MCP server, call one tool, return (outcome, detail)."""
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

            # Check isError on the result object (CallToolResult)
            is_error = getattr(result, "isError", False)

            if isinstance(result, list):
                text = " ".join(
                    getattr(item, "text", str(item)) for item in result
                )
            elif hasattr(result, "content"):
                # CallToolResult — extract text from content list
                text = " ".join(
                    getattr(item, "text", str(item)) for item in result.content
                )
            else:
                text = str(result)

            lower = text.lower()
            deny_keywords = ("denied", "insufficient", "trust",
                             "badge_missing", "badge_invalid", "badge_expired",
                             "badge_revoked", "not_allowed", "issuer_untrusted",
                             "policy_denied")
            if is_error or any(kw in lower for kw in deny_keywords):
                return ("DENY", text)
            if is_error:
                return ("ERROR", text)
            return ("ALLOW", text)

    except Exception as exc:
        msg = str(exc)
        lower = msg.lower()
        deny_keywords = ("denied", "guard", "trust",
                         "badge_missing", "badge_invalid", "badge_expired",
                         "badge_revoked", "not_allowed", "issuer_untrusted",
                         "policy_denied")
        if any(kw in lower for kw in deny_keywords):
            return ("DENY", msg)
        return ("ERROR", msg)


async def run_four_scenarios(
    trusted_badge: str | None,
    untrusted_badge: str | None,
) -> list[tuple[str, str]]:
    """
    Run the standard four scenarios and return results.

    Returns list of (outcome, detail) tuples.
    """
    results = []

    # S1: Trusted → get_price
    scenario_header(1, "trusted (DV)", "get_price", "?")
    outcome, detail = await call_tool(trusted_badge, "get_price", {"sku": "WIDGET-A"})
    result_line(outcome, detail)
    results.append((outcome, detail))

    # S2: Trusted → place_order
    scenario_header(2, "trusted (DV)", "place_order", "?")
    outcome, detail = await call_tool(
        trusted_badge, "place_order", {"sku": "WIDGET-B", "quantity": 2}
    )
    result_line(outcome, detail)
    results.append((outcome, detail))

    # S3: Untrusted → get_price
    scenario_header(3, "untrusted", "get_price", "?")
    outcome, detail = await call_tool(untrusted_badge, "get_price", {"sku": "WIDGET-C"})
    result_line(outcome, detail)
    results.append((outcome, detail))

    # S4: Untrusted → place_order
    scenario_header(4, "untrusted", "place_order", "?")
    outcome, detail = await call_tool(
        untrusted_badge, "place_order", {"sku": "WIDGET-A", "quantity": 1}
    )
    result_line(outcome, detail)
    results.append((outcome, detail))

    return results


# ── Main demo ────────────────────────────────────────────────────────────


async def run_demo() -> None:
    banner("CapiscIO Demo Two — Policy as Code")

    # ── Connect agents ───────────────────────────────────────────────
    print(f"{BOLD}Connecting agents to CapiscIO registry...{RESET}")
    print(f"  Server URL: {os.environ.get('CAPISCIO_SERVER_URL', 'https://dev.registry.capisc.io')}")

    print("\n  Connecting trusted agent (with DV badge)...")
    trusted = trusted_agent.connect()
    trusted_badge = trusted.get_badge()
    if not trusted_badge:
        import time
        print("    Badge: ⏳ waiting for BadgeKeeper...")
        for _ in range(10):
            time.sleep(1)
            trusted_badge = trusted.get_badge()
            if trusted_badge:
                break
    print(f"    DID  : {trusted.did}")
    print(f"    Badge: {'✓ obtained' if trusted_badge else '✗ none'}")

    print("\n  Connecting untrusted agent (no badge)...")
    untrusted = untrusted_agent.connect()
    untrusted_badge = untrusted.get_badge()
    print(f"    DID  : {untrusted.did}")
    print(f"    Badge: {'✗ none (as expected)' if not untrusted_badge else '? unexpected'}")

    # ── Phase 1: Baseline ────────────────────────────────────────────
    phase_header(
        1,
        "Baseline",
        "baseline.yaml",
        "Trust levels as coded — @guard levels apply",
    )
    policy_table([
        ("trusted (DV)", "get_price", "ALLOW", "0 ≤ DV"),
        ("trusted (DV)", "place_order", "ALLOW", "DV ≥ DV"),
        ("untrusted", "get_price", "ALLOW", "open tool"),
        ("untrusted", "place_order", "DENY", "no badge < DV"),
    ])

    await run_four_scenarios(trusted_badge, untrusted_badge)

    # ── Pause for policy switch ──────────────────────────────────────
    print(f"\n{YELLOW}{'─' * 60}{RESET}")
    print(f"{YELLOW}  ACTION REQUIRED:{RESET}")
    print(f"  Switch to the {BOLD}lockdown{RESET} policy in the dashboard:")
    print(f"    {CYAN}https://dev.app.capisc.io{RESET} → Policies → Approve 'lockdown'")
    print("  Wait a few seconds for the PDP bundle to refresh.")
    print(f"{YELLOW}{'─' * 60}{RESET}")
    input(f"\n  Press {BOLD}Enter{RESET} when the lockdown policy is active... ")

    # ── Phase 2: Lockdown ────────────────────────────────────────────
    phase_header(
        2,
        "Lockdown",
        "lockdown.yaml",
        "Global min_trust_level=EV — everything denied",
    )
    policy_table([
        ("trusted (DV)", "get_price", "DENY", "DV < EV"),
        ("trusted (DV)", "place_order", "DENY", "DV < EV"),
        ("untrusted", "get_price", "DENY", "no badge < EV"),
        ("untrusted", "place_order", "DENY", "no badge < EV"),
    ])

    await run_four_scenarios(trusted_badge, untrusted_badge)

    # ── Pause for policy switch ──────────────────────────────────────
    print(f"\n{YELLOW}{'─' * 60}{RESET}")
    print(f"{YELLOW}  ACTION REQUIRED:{RESET}")
    print(f"  Switch to the {BOLD}selective{RESET} policy in the dashboard:")
    print(f"    {CYAN}https://dev.app.capisc.io{RESET} → Policies → Approve 'selective'")
    print("  Wait a few seconds for the PDP bundle to refresh.")
    print(f"{YELLOW}{'─' * 60}{RESET}")
    input(f"\n  Press {BOLD}Enter{RESET} when the selective policy is active... ")

    # ── Phase 3: Selective ───────────────────────────────────────────
    phase_header(
        3,
        "Selective",
        "selective.yaml",
        "get_price overridden to require DV — no code change needed",
    )
    policy_table([
        ("trusted (DV)", "get_price", "ALLOW", "DV ≥ DV"),
        ("trusted (DV)", "place_order", "ALLOW", "DV ≥ DV"),
        ("untrusted", "get_price", "DENY", "no badge < DV"),
        ("untrusted", "place_order", "DENY", "no badge < DV"),
    ])

    await run_four_scenarios(trusted_badge, untrusted_badge)

    # ── Summary ──────────────────────────────────────────────────────
    banner("Summary")
    print("  Three policies, three different enforcement outcomes —")
    print("  all without touching a single line of application code.")
    print()
    print("  The platform admin changed the org policy in the dashboard.")
    print("  The embedded PDP picked up the new policy bundle, and")
    print("  the @guard decorator enforced the updated rules instantly.")
    print()
    print(f"  {BOLD}Key takeaway:{RESET}")
    print("    Trust enforcement is a PLATFORM concern, not an app concern.")
    print("    Developers set code-level floors with @guard.")
    print("    Admins layer org policy on top — at runtime.")
    print()
    print(f"  View audit trail: {CYAN}https://dev.app.capisc.io{RESET}")
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

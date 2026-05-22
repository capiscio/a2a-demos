#!/usr/bin/env python3
"""
Policy Demo — "Policy as Code"

Shows how org-level policy changes alter enforcement at runtime
WITHOUT any code changes or redeployments.  The same MCP server and
agents produce different ALLOW/DENY outcomes depending on which
policy the admin has activated.

Three phases (presenter switches policies in the dashboard between them):

  Phase 1 — Baseline
    Sensitive tools require a CA-issued badge.  Badged agents can
    call get_price and place_order.  Unbadged agents can only
    call get_price.

  Phase 2 — Lockdown
    Global allowlist set to a non-existent DID — ALL agents
    (including badged) are denied everything.  Emergency kill switch.

  Phase 3 — Selective
    get_price overridden to require a badge — a "public" tool
    becomes restricted without any code change.  Badged agents
    still work; unbadged agents are now denied even get_price.

Usage:
    source .venv/bin/activate
    python run_demo.py
    python run_demo.py --verbose  # Show raw request payloads with badge claims

Prerequisites:
    - .env file with credentials
    - Run scripts/setup_policies.py first to create the three policies
    - Baseline policy must be the initial active policy
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

# Suppress gRPC C-core noise (must be before any gRPC import)
os.environ.setdefault("GRPC_VERBOSITY", "NONE")
os.environ.setdefault("GRPC_TRACE", "")


def _cleanup_core_processes() -> None:
    """Kill any lingering capiscio-core (rpc) subprocesses."""
    try:
        result = subprocess.run(
            ["pkill", "-f", "capiscio rpc"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            print("  [cleanup] Terminated stale capiscio-core processes.")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # pkill not available or timed out


# Kill stale cores from previous runs, and register cleanup for exit.
_cleanup_core_processes()
atexit.register(_cleanup_core_processes)

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stderr,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("capiscio_sdk.connect").setLevel(logging.ERROR)

logging.getLogger("capiscio_mcp").setLevel(logging.WARNING)
logging.getLogger("capiscio_sdk").setLevel(logging.WARNING)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from capiscio_mcp.integrations.mcp import CapiscioMCPClient  # noqa: E402

# ── CLI flags ────────────────────────────────────────────────────────────
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

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


def result_line(outcome: str, detail: str, ms: int = 0) -> None:
    color = GREEN if outcome == "ALLOW" else RED
    symbol = "✓" if outcome == "ALLOW" else "✗"
    timing = f"  {DIM}({ms}ms){RESET}" if ms else ""
    print(f"    {color}{symbol} {outcome}{RESET} — {detail}{timing}")


def pause(hint: str = "") -> None:
    """Wait for the presenter to press Enter before continuing."""
    msg = f"\n  {YELLOW}▸ Press Enter to continue{RESET}"
    if hint:
        msg += f"  {YELLOW}({hint}){RESET}"
    input(msg + " ")
    print()


def policy_table(rows: list[tuple[str, str, str, str]]) -> None:
    """Print expected outcomes table for a phase."""
    print(f"\n  {DIM}{'Agent':<22} {'Tool':<18} {'Expected':<8}{RESET}")
    print(f"  {DIM}{'─' * 22} {'─' * 18} {'─' * 8}{RESET}")
    for agent, tool, expected, reason in rows:
        color = GREEN if expected == "ALLOW" else RED
        print(f"  {agent:<22} {tool:<18} {color}{expected:<8}{RESET} {DIM}{reason}{RESET}")


def show_policy_yaml(policy_name: str) -> None:
    """Display the policy YAML contents for the current phase."""
    policy_path = os.path.join(os.path.dirname(__file__), "policies", f"{policy_name}.yaml")
    if not os.path.exists(policy_path):
        return
    with open(policy_path) as f:
        content = f.read()
    # Strip leading comment block (lines starting with #)
    lines = content.splitlines()
    yaml_lines = []
    past_comments = False
    for line in lines:
        if not past_comments and (line.startswith("#") or line.strip() == ""):
            continue
        past_comments = True
        yaml_lines.append(line)
    print(f"\n  {DIM}── {policy_name}.yaml ──{RESET}")
    for line in yaml_lines:
        print(f"  {YELLOW}{line}{RESET}")
    print()


# ── Verbose request logging ─────────────────────────────────────────────


def _decode_badge_claims(badge_jws: str | None) -> dict | None:
    """Decode the payload of a JWS compact badge for verbose display."""
    if not badge_jws:
        return None
    try:
        payload_b64 = badge_jws.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return None


def _verbose_log(
    tool_name: str,
    args: dict,
    badge_jws: str | None,
) -> None:
    """Print the raw request payload when --verbose is active."""
    if not VERBOSE:
        return

    print(f"\n    {DIM}┌─ Request ──────────────────────────────────────{RESET}")
    print(f"    {DIM}│ method : tools/call{RESET}")
    print(f"    {DIM}│ tool   : {tool_name}{RESET}")
    print(f"    {DIM}│ args   : {json.dumps(args)}{RESET}")

    if badge_jws:
        trunc = badge_jws[:40] + "…" + badge_jws[-12:]
        print(f"    {DIM}│ _meta.capiscio_caller_badge : {trunc}{RESET}")

        claims = _decode_badge_claims(badge_jws)
        if claims:
            print(f"    {DIM}│   iss : {claims.get('iss', '—')}{RESET}")
            print(f"    {DIM}│   sub : {claims.get('sub', '—')}{RESET}")
            print(f"    {DIM}│   jti : {claims.get('jti', '—')}{RESET}")
            iat = claims.get("iat")
            exp = claims.get("exp")
            if iat:
                print(f"    {DIM}│   iat : {iat}  ({time.strftime('%H:%M:%S', time.localtime(iat))}){RESET}")
            if exp:
                print(f"    {DIM}│   exp : {exp}  ({time.strftime('%H:%M:%S', time.localtime(exp))}){RESET}")
            vc = claims.get("vc", {})
            cs = vc.get("credentialSubject", {})
            level = cs.get("level")
            if level is not None:
                print(f"    {DIM}│   trust_level : {level}{RESET}")
    else:
        print(f"    {DIM}│ _meta.capiscio_caller_badge : (none){RESET}")

    print(f"    {DIM}└────────────────────────────────────────────────{RESET}")


# ── Tool caller ──────────────────────────────────────────────────────────

SERVER_CMD = sys.executable
SERVER_ARGS = [os.path.join(os.path.dirname(__file__), "server", "main.py")]

DENY_KEYWORDS = (
    "denied", "insufficient", "trust", "guard",
    "badge_missing", "badge_invalid", "badge_expired",
    "badge_revoked", "not_allowed", "issuer_untrusted",
    "policy_denied",
)


def _parse_result(result: object) -> tuple[str, str]:
    """Extract (outcome, detail) from a CallToolResult."""
    is_error = getattr(result, "isError", False)

    if isinstance(result, list):
        text = " ".join(getattr(item, "text", str(item)) for item in result)
    elif hasattr(result, "content"):
        text = " ".join(
            getattr(item, "text", str(item)) for item in result.content
        )
    else:
        text = str(result)

    lower = text.lower()
    if any(kw in lower for kw in DENY_KEYWORDS):
        return ("DENY", text)
    if is_error:
        return ("ERROR", text)
    return ("ALLOW", text)


async def _safe_call(
    client: CapiscioMCPClient,
    tool_name: str,
    args: dict,
) -> tuple[str, str, int]:
    """Call a tool, catching exceptions as DENY/ERROR outcomes.

    Returns (outcome, detail, elapsed_ms).
    """
    _verbose_log(tool_name, args, client._credential.badge_jws)
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


async def run_four_scenarios(
    client: CapiscioMCPClient,
    trusted: object,
    untrusted: object,
    expected: list[str],
) -> bool:
    """
    Run the standard four scenarios using a single live server session.

    Swaps the client badge between calls — the server subprocess (and its
    Go core sidecar + PDP cache) stays warm across all calls.

    trusted/untrusted: AgentIdentity objects — get_badge() is called fresh
    each time to avoid using an expired badge.

    expected: list of 4 expected outcomes, e.g. ["ALLOW", "ALLOW", "ALLOW", "DENY"]
    Returns True if all outcomes match expected.
    """
    # Pre-check: ensure the badged identity actually has a badge.
    # The keeper may need extra time after a long pause (user reading slides).
    badge = trusted.get_badge()
    if not badge:
        print(f"  {YELLOW}⏳ Badge not available — waiting for BadgeKeeper...{RESET}")
        for i in range(15):
            await asyncio.sleep(1)
            badge = trusted.get_badge()
            if badge:
                print(f"  {GREEN}✓ Badge obtained after {i + 1}s{RESET}")
                break
        if not badge:
            keeper = getattr(trusted, '_keeper', None)
            running = keeper.is_running() if keeper else False
            print(f"  {RED}✗ Badge still unavailable after 15s "
                  f"(keeper={'running' if running else 'STOPPED'}){RESET}")
            print(f"  {DIM}  Badged scenarios will fail with badge_missing.{RESET}")

    scenarios = [
        (1, "badged", "get_price", {"sku": "WIDGET-A"}, trusted),
        (2, "badged", "place_order", {"sku": "WIDGET-B", "quantity": 2}, trusted),
        (3, "unbadged", "get_price", {"sku": "WIDGET-C"}, untrusted),
        (4, "unbadged", "place_order", {"sku": "WIDGET-A", "quantity": 1}, untrusted),
    ]

    results: list[tuple[str, str]] = []
    for num, agent, tool, args, identity in scenarios:
        client.set_badge(identity.get_badge())
        scenario_header(num, agent, tool, "?")
        outcome, detail, ms = await _safe_call(client, tool, args)
        result_line(outcome, detail, ms)
        results.append((outcome, detail))

    # ── Phase verdict ────────────────────────────────────────────────
    actuals = [r[0] for r in results]
    passed = all(a == e for a, e in zip(actuals, expected))
    if passed:
        print(f"\n  {GREEN}{BOLD}✓ PHASE PASSED{RESET} — all 4 scenarios matched expected outcomes")
    else:
        print(f"\n  {RED}{BOLD}✗ PHASE FAILED{RESET} — mismatches:")
        labels = [
            "badged → get_price",
            "badged → place_order",
            "unbadged → get_price",
            "unbadged → place_order",
        ]
        for label, exp, act in zip(labels, expected, actuals):
            if exp != act:
                print(f"    {label}: expected {exp}, got {RED}{act}{RESET}")
    return passed


# ── Main demo ────────────────────────────────────────────────────────────


async def run_demo() -> None:
    banner("CapiscIO Policy Demo — Policy as Code")

    # ── Connect agents ───────────────────────────────────────────────
    print(f"{BOLD}Connecting agents to CapiscIO registry...{RESET}")
    print(f"  Server URL: {os.environ.get('CAPISCIO_SERVER_URL', 'https://registry.capisc.io')}")

    print("\n  Connecting badged agent (CA-issued badge)...")
    trusted = trusted_agent.connect()
    trusted_badge = trusted.get_badge()
    if not trusted_badge:
        print("    Badge: ⏳ waiting for BadgeKeeper...")
        for _ in range(10):
            await asyncio.sleep(1)
            trusted_badge = trusted.get_badge()
            if trusted_badge:
                break
    print(f"    DID  : {trusted.did}")
    print(f"    Badge: {'✓ obtained' if trusted_badge else '✗ none'}")

    print("\n  Connecting unbadged agent (no badge)...")
    untrusted = untrusted_agent.connect()
    untrusted_badge = untrusted.get_badge()
    print(f"    DID  : {untrusted.did}")
    print(f"    Badge: {'✗ none (as expected)' if not untrusted_badge else '? unexpected'}")

    # ── Start MCP server (one subprocess for ALL phases) ─────────────
    # The same server stays alive while the admin switches policies
    # in the dashboard.  The embedded PDP picks up the new policy
    # bundle automatically — no restart needed.
    async with CapiscioMCPClient(
        command=SERVER_CMD,
        args=SERVER_ARGS,
        badge=trusted_badge,
        min_trust_level=0,
        fail_on_unverified=False,
    ) as client:
        # Warm up the Go core sidecar (first call pays startup cost)
        try:
            await client.call_tool("get_price", {"sku": "WARMUP"})
        except Exception:
            pass

        # ── Phase 1: Baseline ────────────────────────────────────────
        phase_header(
            1,
            "Baseline",
            "baseline.yaml",
            "Sensitive tools require a CA-issued badge",
        )
        policy_table([
            ("badged", "get_price", "ALLOW", "open tool"),
            ("badged", "place_order", "ALLOW", "has badge"),
            ("unbadged", "get_price", "ALLOW", "open tool"),
            ("unbadged", "place_order", "DENY", "no badge"),
        ])

        print(f"\n{YELLOW}{'─' * 60}{RESET}")
        print(f"{YELLOW}  ACTION REQUIRED:{RESET}")
        print(f"  Apply the {BOLD}baseline{RESET} policy in the dashboard:")
        print(f"    1. Open {CYAN}https://app.capisc.io{RESET} → Policies")
        print(f"    2. Create/activate the {BOLD}baseline{RESET} policy with this YAML:")
        show_policy_yaml("baseline")
        print("    3. Wait a few seconds for the PDP bundle to refresh")
        print(f"{YELLOW}{'─' * 60}{RESET}")
        input(f"\n  Press {BOLD}Enter{RESET} when the baseline policy is active... ")

        await run_four_scenarios(client, trusted, untrusted,
                                expected=["ALLOW", "ALLOW", "ALLOW", "DENY"])

        # ── Phase 2: Lockdown ────────────────────────────────────────
        phase_header(
            2,
            "Lockdown",
            "lockdown.yaml",
            "DID allowlist — only explicitly listed agents can access anything",
        )
        policy_table([
            ("badged", "get_price", "DENY", "not in allowlist"),
            ("badged", "place_order", "DENY", "not in allowlist"),
            ("unbadged", "get_price", "DENY", "not in allowlist"),
            ("unbadged", "place_order", "DENY", "not in allowlist"),
        ])

        print(f"\n{YELLOW}{'─' * 60}{RESET}")
        print(f"{YELLOW}  ACTION REQUIRED:{RESET}")
        print(f"  Switch to the {BOLD}lockdown{RESET} policy in the dashboard:")
        print(f"    1. Open {CYAN}https://app.capisc.io{RESET} → Policies")
        print(f"    2. Activate the {BOLD}lockdown{RESET} policy with this YAML:")
        show_policy_yaml("lockdown")
        print("    3. Wait a few seconds for the PDP bundle to refresh")
        print(f"{YELLOW}{'─' * 60}{RESET}")
        input(f"\n  Press {BOLD}Enter{RESET} when the lockdown policy is active... ")

        await run_four_scenarios(client, trusted, untrusted,
                                expected=["DENY", "DENY", "DENY", "DENY"])

        # ── Phase 3: Selective ───────────────────────────────────────
        phase_header(
            3,
            "Selective",
            "selective.yaml",
            "get_price now requires a badge — no code change needed",
        )
        policy_table([
            ("badged", "get_price", "ALLOW", "has badge"),
            ("badged", "place_order", "ALLOW", "has badge"),
            ("unbadged", "get_price", "DENY", "no badge"),
            ("unbadged", "place_order", "DENY", "no badge"),
        ])

        print(f"\n{YELLOW}{'─' * 60}{RESET}")
        print(f"{YELLOW}  ACTION REQUIRED:{RESET}")
        print(f"  Switch to the {BOLD}selective{RESET} policy in the dashboard:")
        print(f"    1. Open {CYAN}https://app.capisc.io{RESET} → Policies")
        print(f"    2. Activate the {BOLD}selective{RESET} policy with this YAML:")
        show_policy_yaml("selective")
        print("    3. Wait a few seconds for the PDP bundle to refresh")
        print(f"{YELLOW}{'─' * 60}{RESET}")
        input(f"\n  Press {BOLD}Enter{RESET} when the selective policy is active... ")

        await run_four_scenarios(client, trusted, untrusted,
                                expected=["ALLOW", "ALLOW", "DENY", "DENY"])

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
    print(f"  View audit trail: {CYAN}https://app.capisc.io{RESET}")
    print()

    # Clean up
    logging.getLogger("capiscio_sdk.badge_keeper").setLevel(logging.CRITICAL)
    trusted.close()
    untrusted.close()


def main() -> None:
    # Suppress noisy shutdown tracebacks on Ctrl+C — the async generators
    # and gRPC streams complain about unclean teardown, which is expected.
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
    finally:
        _cleanup_core_processes()


if __name__ == "__main__":
    main()

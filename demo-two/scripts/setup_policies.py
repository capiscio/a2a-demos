#!/usr/bin/env python3
"""
Demo Two — Policy Setup Script.

Pre-creates three policy proposals in the CapiscIO registry and
approves the baseline policy as the active default.

Requires CAPISCIO_ADMIN_JWT and CAPISCIO_ORG_ID in .env.

Usage:
    source .venv/bin/activate
    python scripts/setup_policies.py
"""

import os
import sys

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ───────────────────────────────────────────────────────────────

SERVER_URL = os.environ.get("CAPISCIO_SERVER_URL", "https://dev.registry.capisc.io")
ORG_ID = os.environ.get("CAPISCIO_ORG_ID")
ADMIN_JWT = os.environ.get("CAPISCIO_ADMIN_JWT")

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "..", "policies")

BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def die(msg: str) -> None:
    print(f"{RED}Error:{RESET} {msg}", file=sys.stderr)
    sys.exit(1)


def check_env() -> None:
    if not ORG_ID:
        die("CAPISCIO_ORG_ID not set in .env")
    if not ADMIN_JWT:
        die(
            "CAPISCIO_ADMIN_JWT not set in .env\n"
            "  Generate a temporary JWT from the dashboard:\n"
            "  Dashboard → Developer → API Tokens"
        )


def create_policy(client: httpx.Client, name: str, yaml_path: str) -> str | None:
    """Create a policy proposal. Returns the proposal ID or None on error."""
    with open(yaml_path) as f:
        raw = f.read()

    # Validate YAML is parseable
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        print(f"  {RED}✗{RESET} Invalid YAML in {name}: {exc}")
        return None

    if doc.get("version") != "1":
        print(f"  {RED}✗{RESET} {name}: version must be \"1\"")
        return None

    url = f"{SERVER_URL}/v1/orgs/{ORG_ID}/policy/org"
    resp = client.post(url, json={"yaml_content": raw})

    if resp.status_code not in (200, 201):
        print(f"  {RED}✗{RESET} {name}: {resp.status_code} — {resp.text}")
        return None

    data = resp.json()
    proposal_id = data.get("id") or data.get("proposal_id") or data.get("document_id")
    print(f"  {GREEN}✓{RESET} {name}: proposal {proposal_id}")
    return proposal_id


def approve_policy(client: httpx.Client, proposal_id: str, name: str) -> bool:
    """Approve a policy proposal to make it the active org policy."""
    url = f"{SERVER_URL}/v1/orgs/{ORG_ID}/policy/proposals/{proposal_id}/approve"
    resp = client.post(url)

    if resp.status_code not in (200, 204):
        print(f"  {RED}✗{RESET} Approve {name}: {resp.status_code} — {resp.text}")
        return False

    print(f"  {GREEN}✓{RESET} {name}: approved (now active)")
    return True


def main() -> None:
    check_env()

    print(f"\n{CYAN}{'═' * 60}{RESET}")
    print(f"{CYAN}  Demo Two — Policy Setup{RESET}")
    print(f"{CYAN}{'═' * 60}{RESET}\n")
    print(f"  Registry : {SERVER_URL}")
    print(f"  Org ID   : {ORG_ID}")
    print()

    headers = {
        "Authorization": f"Bearer {ADMIN_JWT}",
        "Content-Type": "application/json",
    }
    client = httpx.Client(headers=headers, timeout=30.0)

    # ── Create all three policy proposals ────────────────────────────
    print(f"{BOLD}Creating policy proposals…{RESET}")

    policies = [
        ("baseline", os.path.join(POLICIES_DIR, "baseline.yaml")),
        ("lockdown", os.path.join(POLICIES_DIR, "lockdown.yaml")),
        ("selective", os.path.join(POLICIES_DIR, "selective.yaml")),
    ]

    proposal_ids: dict[str, str] = {}
    for name, path in policies:
        pid = create_policy(client, name, path)
        if pid:
            proposal_ids[name] = pid

    if not proposal_ids:
        die("No policies were created. Check your JWT and org ID.")

    print()

    # ── Approve baseline as the initial active policy ────────────────
    if "baseline" in proposal_ids:
        print(f"{BOLD}Activating baseline policy…{RESET}")
        approve_policy(client, proposal_ids["baseline"], "baseline")
        print()

    # ── Summary ──────────────────────────────────────────────────────
    print(f"{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}  Policy proposals ready:{RESET}")
    for name, pid in proposal_ids.items():
        status = "ACTIVE" if name == "baseline" else "proposal"
        color = GREEN if status == "ACTIVE" else YELLOW
        print(f"    {name:12s} → {pid}  [{color}{status}{RESET}]")
    print()
    print("  To switch policies during the demo:")
    print(f"    1. Open {CYAN}https://dev.app.capisc.io{RESET}")
    print("    2. Navigate to your org → Policies")
    print("    3. Click 'Approve' on the desired policy proposal")
    print()
    print("  Or approve via API:")
    for name, pid in proposal_ids.items():
        if name != "baseline":
            print("    python -c \"import httpx; httpx.Client(headers={{...}}).post(")
            print(f"      '{SERVER_URL}/v1/orgs/{ORG_ID}/policy/proposals/{pid}/approve')\"")
    print(f"{CYAN}{'═' * 60}{RESET}\n")

    client.close()


if __name__ == "__main__":
    main()

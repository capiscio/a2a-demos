# Demo Two — "Policy as Code"

Demonstrates how org-level policy changes alter enforcement at runtime WITHOUT any code changes or redeployments.

## What It Shows

The same MCP server and agents produce different ALLOW/DENY outcomes depending on which policy the admin has activated in the CapiscIO dashboard.

### Three Phases

| Phase | Policy | Effect |
|-------|--------|--------|
| 1 — Baseline | Default enforcement | Trust levels as coded in `@guard` decorators |
| 2 — Lockdown | Global `min_trust_level` raised to EV | ALL agents denied everything |
| 3 — Selective | `get_price` overridden to require DV | Trusted (DV) still works; untrusted denied even `get_price` |

### Tools (same as Demo One)

| Tool | Code-level Min Trust | Notes |
|------|---------------------|-------|
| `get_price` | 0 (open) | Overridden by policy in Phase 3 |
| `place_order` | 1 (PoP) | Denied in Phase 2 for all agents |
| `cancel_all_orders` | 2 (DV) | Denied in Phase 2 for all agents |

## Prerequisites

- Python 3.11+
- A CapiscIO account with an API key
- An MCP server registered in the CapiscIO dashboard
- Policies configured in the dashboard (see `scripts/setup_policies.py`)

## Setup

```bash
# 1. Create and populate .env
cp .env.example .env
# Required vars: CAPISCIO_API_KEY, CAPISCIO_SERVER_ID, CAPISCIO_SERVER_URL

# 2. Run setup (creates venv, installs deps)
./setup.sh

# 3. Create the three policies in the registry
source .venv/bin/activate
python scripts/setup_policies.py
```

## Running

```bash
source .venv/bin/activate
python run_demo.py
```

The demo pauses between phases so the presenter can switch the active policy in the CapiscIO dashboard. Each phase re-runs the same agent calls to show the changed enforcement.

## How It Works

1. The MCP server fetches its policy context from the registry on each request
2. Policy context includes trust-level overrides set by the org admin
3. The `@guard` decorator evaluates both the code-level minimum AND the policy minimum
4. The higher of the two wins — policy can only raise trust requirements, never lower them

# Demo One — "Zero to Enforcement"

Demonstrates CapiscIO trust enforcement on an MCP server with three tools at different trust levels.

## What It Shows

An MCP server exposes tools with per-tool trust requirements. Agents with valid badges can access higher-trust tools, while agents without badges are restricted.

| Tool | Min Trust Level | Access |
|------|----------------|--------|
| `get_price` | 0 (open) | Any agent |
| `place_order` | 1 (PoP) | Badged agents (key-ownership proved) |
| `cancel_all_orders` | 2 (DV) | Domain-validated agents |

### Scenarios

| # | Agent | Tool | Expected |
|---|-------|------|----------|
| 1 | Trusted (badged) | `get_price` | ALLOW |
| 2 | Trusted (badged) | `place_order` | ALLOW |
| 3 | Untrusted (no badge) | `get_price` | ALLOW |
| 4 | Untrusted (no badge) | `place_order` | DENY |

## Prerequisites

- Python 3.11+
- A CapiscIO account with an API key
- An MCP server registered in the CapiscIO dashboard

## Setup

```bash
# 1. Create and populate .env (copy from .env.example or set manually)
cp .env.example .env
# Required vars: CAPISCIO_API_KEY, CAPISCIO_SERVER_ID, CAPISCIO_SERVER_URL

# 2. Run setup (creates venv, installs deps, pre-downloads binary)
./setup.sh
```

## Running

```bash
source .venv/bin/activate
python run_demo.py
```

The demo runs the MCP server as a subprocess (stdio transport), then executes each scenario sequentially, printing ALLOW/DENY results.

## How It Works

1. The MCP server starts and obtains its identity (DID + badge) from the registry via `MCPServerIdentity.from_env()`
2. The trusted agent connects to the registry, obtains a badge via PoP (RFC-003)
3. The untrusted agent connects without a badge
4. Each agent calls tools — the `@guard` decorator on the server enforces per-tool trust levels

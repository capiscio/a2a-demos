# Enforcement Demo — "Zero to Enforcement"

5 minutes from zero to trust-enforced MCP tools.

An MCP server with three tools at different trust levels. The demo starts by verifying the server's cryptographic identity (DID + badge), then runs four enforcement scenarios: a trusted agent (with a CapiscIO badge) can call restricted tools while an untrusted agent gets denied.

## Quick Start

```bash
# 1. Setup
cd enforcement-demo
./setup.sh                    # Creates venv, installs deps, downloads binary

# 2. Add your credentials
                              # Edit .env — add CAPISCIO_API_KEY (see below)

# 3. Run
source .venv/bin/activate
python run_demo.py            # Interactive — pauses between scenarios
python run_demo.py --auto     # Non-interactive — runs straight through
```

### `.env` values

| Variable | Required? | Default | Notes |
|----------|-----------|---------|-------|
| `CAPISCIO_API_KEY` | **Yes** | — | From [app.capisc.io](https://app.capisc.io) → Settings → API Keys |
| `CAPISCIO_SERVER_URL` | No | `https://registry.capisc.io` | Python SDK: badge issuance, agent registration |
| `CAPISCIO_REGISTRY_ENDPOINT` | No | `https://registry.capisc.io` | Go binary: JWKS badge verification. Must match `SERVER_URL` |
| `CAPISCIO_SERVER_ID` | No | `auto` | Auto-registers an MCP server on first run. Or paste a UUID from the dashboard |

## What You'll See

The demo first verifies the MCP server's identity, then runs 4 enforcement scenarios:

### Server Identity Verification

Before any tool calls, the client verifies the server's DID and badge from the MCP `initialize` response. This is bidirectional trust — the server proves its identity to the client, and the client proves its trust to the server via badges.

### Enforcement Scenarios

| # | Agent | Tool | Result | Why |
|---|-------|------|--------|-----|
| 1 | Trusted (badged) | `get_price` | ✓ ALLOW | Open tool, any agent can call it |
| 2 | Trusted (badged) | `place_order` | ✓ ALLOW | Badge proves key ownership (PoP) |
| 3 | Untrusted (no badge) | `get_price` | ✓ ALLOW | Open tool — no badge needed |
| 4 | Untrusted (no badge) | `place_order` | ✗ DENY | No badge → can't meet trust level 1 |

### Expected output

```
══════════════════════════════════════════════════════════════
  CapiscIO Enforcement Demo — Zero to Enforcement
══════════════════════════════════════════════════════════════

Connecting agents to CapiscIO registry...
  Server URL: https://registry.capisc.io

  Connecting trusted agent (with badge)...
    DID  : did:web:registry.capisc.io:agents:...
    Badge: ✓ obtained

  Connecting untrusted agent (no badge)...
    DID  : did:web:registry.capisc.io:agents:...
    Badge: ✗ none (as expected)

══════════════════════════════════════════════════════════════
  Server Identity Verification
══════════════════════════════════════════════════════════════

  Server DID          : did:web:registry.capisc.io:servers:...
  Server trust level  : 2
  Server state        : VERIFIED

  The client verified the server's DID + badge from the
  initialize response _meta before calling any tools.

  Bidirectional trust:
    • Servers prove identity to clients (DID + badge in _meta)
    • Clients prove trust to servers (badge per tool call)

══════════════════════════════════════════════════════════════
  Running Enforcement Scenarios
══════════════════════════════════════════════════════════════

── Scenario 1 ──────────────────────────────────────────
  Agent : trusted (badged)
  Tool  : get_price (min_trust_level=0)
  Expect: ALLOW

  Result: ALLOW — Widget Alpha: $9.99

── Scenario 4 ──────────────────────────────────────────
  Agent : untrusted (no badge)
  Tool  : place_order (min_trust_level=1)
  Expect: DENY

  Result: DENY — badge_missing: badge required but not provided

══════════════════════════════════════════════════════════════
  Results
══════════════════════════════════════════════════════════════

  #    Agent                  Tool             Expected   Actual
  ──── ────────────────────── ──────────────── ────────── ──────────
  1    trusted (badged)       get_price        ALLOW      ALLOW      ✓
  2    trusted (badged)       place_order      ALLOW      ALLOW      ✓
  3    untrusted (no badge)   get_price        ALLOW      ALLOW      ✓
  4    untrusted (no badge)   place_order      DENY       DENY       ✓

  All 4 scenarios passed.

  Key takeaways:
    • Access is enforced per-tool, earned by badge, and
      revocable via agent suspension — all via @server.tool(min_trust_level=N)
    • The client verified the server's identity before calling any tools
    • Bidirectional trust: servers prove identity to clients,
      clients prove trust to servers — both cryptographically verified
```

## Key Code

**Server** — one decorator per tool:
```python
@server.tool(min_trust_level=0)    # open to all
async def get_price(sku: str) -> str: ...

@server.tool(min_trust_level=1)    # requires PoP badge
async def place_order(sku: str, quantity: int) -> str: ...

@server.tool(min_trust_level=2)    # requires domain validation
async def cancel_all_orders() -> str: ...
```

**Agent** — one line to connect:
```python
identity = CapiscIO.connect(api_key="your-api-key", auto_badge=True)
```

## How It Works

1. The MCP server starts and obtains its identity (DID + badge) via `CapiscioMCPServer.connect()`
2. The client connects and verifies the server's DID + badge from the `initialize` response `_meta`
3. The trusted agent connects to the registry, proves key ownership (PoP), and receives a trust badge
4. The untrusted agent connects but skips badge issuance
5. Each agent calls tools — `@server.tool(min_trust_level=N)` checks the badge's trust level

## Files

```
enforcement-demo/
├── run_demo.py             # Orchestrator — 4 interactive scenarios
├── server/main.py          # MCP server with 3 guarded tools
├── agents/
│   ├── trusted_agent.py    # Badged agent (auto_badge=True)
│   └── untrusted_agent.py  # No-badge agent (auto_badge=False)
├── setup.sh                # One-command environment setup
├── .env.example            # Credential template
└── requirements.txt
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `CAPISCIO_API_KEY not set` | Copy `.env.example` to `.env` and add your key from [app.capisc.io](https://app.capisc.io) |
| `Badge: ✗ none` for trusted agent | Check your API key is valid and the registry URL is reachable |
| `Server ... not found` with a UUID | The server ID doesn't exist in your org. Set `CAPISCIO_SERVER_ID=auto` to create one |
| `ModuleNotFoundError: capiscio_mcp` | Run `./setup.sh` first, then `source .venv/bin/activate` |


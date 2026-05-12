# Enforcement Demo — "Zero to Enforcement"

5 minutes from zero to trust-enforced MCP tools.

An MCP server with three tools at different trust levels. A trusted agent (with a CapiscIO badge) can call restricted tools; an untrusted agent gets denied. Then we revoke the badge live — and even the trusted agent is locked out.

## Quick Start

```bash
# 1. Setup
cd enforcement-demo
./setup.sh                    # Creates venv, installs deps, downloads binary

# 2. Add your credentials
cp .env.example .env          # Then edit .env — see below

# 3. Run
source .venv/bin/activate
python run_demo.py            # Interactive — pauses between scenarios
python run_demo.py --auto     # Non-interactive — runs straight through
```

### `.env` values

| Variable | Required? | Default | Notes |
|----------|-----------|---------|-------|
| `CAPISCIO_API_KEY` | **Yes** | — | From [app.capisc.io](https://app.capisc.io) → Settings → API Keys |
| `CAPISCIO_SERVER_ID` | No | `auto` | Auto-registers an MCP server on first run. Or paste a UUID from the dashboard |
| `CAPISCIO_SERVER_URL` | No | `https://registry.capisc.io` | Only change for self-hosted or staging environments |

## What You'll See

The demo runs 5 scenarios, pausing between each so you can follow along:

| # | Agent | Tool | Result | Why |
|---|-------|------|--------|-----|
| 1 | Trusted (badged) | `get_price` | ✓ ALLOW | Open tool, any agent can call it |
| 2 | Trusted (badged) | `place_order` | ✓ ALLOW | Badge proves key ownership (PoP) |
| 3 | Untrusted (no badge) | `get_price` | ✓ ALLOW | Open tool — no badge needed |
| 4 | Untrusted (no badge) | `place_order` | ✗ DENY | No badge → can't meet trust level 1 |
| 5 | Trusted (badge **revoked**) | `place_order` | ✗ DENY | Badge revoked → trust is gone |

### Expected output

```
══════════════════════════════════════════════════════════════
  CapiscIO Enforcement Demo — Zero to Enforcement
══════════════════════════════════════════════════════════════

Connecting agents to CapiscIO registry...
  Server URL: https://registry.capisc.io

  Connecting trusted agent (with badge)...
    DID  : did:key:z6Mk...
    Badge: ✓ obtained

  Connecting untrusted agent (no badge)...
    DID  : did:key:z6Mk...
    Badge: ✗ none (as expected)

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

── Scenario 5 ──────────────────────────────────────────
  Agent : trusted (badge REVOKED)
  Tool  : place_order (min_trust_level=1)
  Expect: DENY

  Revoking trusted agent's badge...
    ✓ Badge revoked (JTI: a1b2c3d4e5f6…)

  Result: DENY — badge_revoked: badge has been revoked

══════════════════════════════════════════════════════════════
  Results
══════════════════════════════════════════════════════════════

  #    Agent                  Tool             Expected   Actual
  ──── ────────────────────── ──────────────── ────────── ──────────
  1    trusted (badged)       get_price        ALLOW      ALLOW      ✓
  2    trusted (badged)       place_order      ALLOW      ALLOW      ✓
  3    untrusted (no badge)   get_price        ALLOW      ALLOW      ✓
  4    untrusted (no badge)   place_order      DENY       DENY       ✓
  5    trusted (REVOKED)      place_order      DENY       DENY       ✓

  All 5 scenarios passed.

  Key takeaway: Trust is enforced per-tool, earned by proof, and
  revocable in real time — all via the @guard decorator.
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
identity = CapiscIO.connect(api_key="sk_live_...", auto_badge=True)
```

## How It Works

1. The MCP server starts and obtains its identity (DID + badge) via `MCPServerIdentity.from_env()`
2. The trusted agent connects to the registry, proves key ownership (PoP), and receives a trust badge
3. The untrusted agent connects but skips badge issuance
4. Each agent calls tools — the `@guard` decorator on the server checks the badge's trust level
5. The trusted agent's badge is revoked via the API — subsequent calls are denied

## Files

```
enforcement-demo/
├── run_demo.py             # Orchestrator — 5 interactive scenarios
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
| Scenario 5 shows ALLOW after revocation | Badge propagation takes ~2s. If still failing, check your network connection |

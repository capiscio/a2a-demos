# CapiscIO MCP Demo

**"Let's Encrypt for AI agents, including MCP servers"** — a working end-to-end
demonstration of RFC-006 (tool authority) and RFC-007 (server identity disclosure).

---

## What this demo shows

| Feature | Where |
|---------|-------|
| One-line MCP server identity (`MCPServerIdentity.connect()`) | `server/main.py` |
| Automatic key generation + DID derivation | `capiscio_mcp.connect` |
| Server DID injected into every `initialize` response `_meta` | `capiscio_mcp.integrations.mcp` |
| Per-tool trust-level enforcement (`@server.tool(min_trust_level=N)`) | `server/main.py` |
| Client-side server identity verification from `_meta` | `client/main.py` |
| Badge auto-renewal via `ServerBadgeKeeper` | `capiscio_mcp.keeper` |

---

## Quick start (Docker)

### 1. Prerequisites

- Docker + Docker Compose
- A CapiscIO account at [app.capisc.io](https://app.capisc.io)
- An MCP server registered in the dashboard (get its UUID)
- An API key (Settings → API Keys)

### 2. Configure

```bash
cd a2a-demos/mcp-demo
cp .env.example .env
# Edit .env: set CAPISCIO_SERVER_ID and CAPISCIO_API_KEY
```

### 3. Start the stack

```bash
docker compose up --build
```

This starts:
- **`capiscio-server`** on port 8080 (test mode, no Clerk needed)
- **`postgres`** backing the registry
- **`mcp-server`** — the demo MCP server that registers its identity on startup

### 4. Run the client

In a second terminal:

```bash
docker compose run --rm mcp-client
```

---

## Quick start (local / without Docker)

### 1. Install dependencies

```bash
cd a2a-demos/mcp-demo
pip install -r server/requirements.txt
pip install -r client/requirements.txt
```

### 2. Start a local CapiscIO server

```bash
cd ../../capiscio-server
CAPISCIO_TEST_MODE=true make run
```

### 3. Start the MCP server

In a new terminal:
```bash
cd a2a-demos/mcp-demo
export CAPISCIO_SERVER_ID=<your-server-uuid>
export CAPISCIO_API_KEY=<your-api-key>
export CAPISCIO_SERVER_URL=http://localhost:8080
python server/main.py
```

### 4. Run the client (in yet another terminal)

```bash
cd a2a-demos/mcp-demo
export CAPISCIO_SERVER_URL=http://localhost:8080
python client/main.py
```

---

## Expected output

### Server (`server/main.py`)

```
INFO  capiscio_mcp.connect  Generated Ed25519 keypair for MCP server <uuid>...
INFO  capiscio_mcp.connect  Registering DID did:key:z6Mk... with registry...
INFO  capiscio_mcp.connect  Server identity registered: did:key:z6Mk...
INFO  capiscio_mcp.connect  Badge issued for server <uuid>
INFO  capiscio_mcp.keeper   Starting ServerBadgeKeeper for server <uuid> (threshold=30s)
INFO  __main__              Server DID  : did:key:z6Mk...
INFO  __main__              Badge ready : yes
INFO  __main__              Starting MCP server over stdio transport…
```

### Client (`client/main.py`)

```
INFO  __main__  Server DID          : did:key:z6Mk...
INFO  __main__  Server trust level  : 1
INFO  __main__  Server state        : VERIFIED_PRINCIPAL
INFO  __main__  --- list_files /tmp (min_trust_level=0) ---
INFO  __main__  Files: ['...', '...']
INFO  __main__  --- read_file (min_trust_level=2) ---
INFO  __main__  No agent badge provided — read_file will be denied...
INFO  __main__  --- write_file (min_trust_level=3) ---
INFO  __main__  write_file requires trust level 3...
```

---

## Tool trust levels

| Tool | `min_trust_level` | Who can call it |
|------|:-----------------:|-----------------|
| `list_files` | 0 | Anyone (no badge required) |
| `read_file` | 2 | Agents with a level-2 badge |
| `write_file` | 3 | Agents with a level-3 badge |

Set `CAPISCIO_AGENT_BADGE` in the client environment to supply a real badge and
test the higher-trust tools.

---

## Architecture

```
                        MCP stdio transport
 ┌──────────────────┐  ──────────────────────  ┌──────────────────────┐
 │  client/main.py  │  initialize request  ──>  │  server/main.py      │
 │  CapiscioMCP     │  <── initialize result     │  CapiscioMCPServer   │
 │  Client          │     (with _meta:           │  + MCPServerIdentity │
 │                  │      capiscio_server_did   │    .connect()        │
 │  verifies server │      capiscio_server_badge)│                      │
 │  DID + badge     │                            │  @tool(min_trust=2)  │
 └──────────────────┘                            │  async def read_file │
          │                                      └──────────┬───────────┘
          │                                                 │
          └──────────── CapiscIO Registry ─────────────────┘
                        https://registry.capisc.io
                        (or localhost:8080 in test mode)
```

---

## Files

```
mcp-demo/
├── server/
│   ├── main.py              # Guarded MCP filesystem server
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── client/
│   ├── main.py              # Agent that calls the MCP server
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml       # capiscio-server + mcp-server + client
├── .env.example             # Config template
└── README.md                # This file
```

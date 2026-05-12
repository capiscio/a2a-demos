<p align="center">
  <strong>🔒 Trust Infrastructure for AI Agents</strong><br/>
  <a href="https://capisc.io">Website</a> · <a href="https://docs.capisc.io/getting-started/">Get Started</a> · <a href="https://capisc.io/pycon">Meet us at PyCon US 2026</a>
</p>

---

# CapiscIO Demos

> Working examples of CapiscIO's "Let's Encrypt for AI" approach — cryptographic identity, trust badges, and policy enforcement for **MCP servers** and **A2A agents**.

## Demos at a Glance

### Concept Demos — understand CapiscIO security

Self-contained, no LLM required. Each focuses on one security concept with an interactive walkthrough.

| Demo | What it shows | Time | Quick start |
|------|---------------|------|-------------|
| **[Enforcement Demo](#enforcement-demo--zero-to-enforcement)** | `min_trust_level` per tool, badge verification, revocation | 5 min | `cd enforcement-demo && ./setup.sh` |
| **[MCP Guard Demo](#mcp-guard-demo)** | Server identity, client verification, per-tool trust | 5 min | `cd mcp-demo && docker compose up` |

### Integration Demos — CapiscIO with real AI frameworks

Requires `OPENAI_API_KEY`. Long-running HTTP servers using the A2A protocol with real LLM calls.

| Demo | What it shows | Time | Quick start |
|------|---------------|------|-------------|
| **[Agent Guard Demos](#agent-guard-demos)** | LangChain, CrewAI, LangGraph agents with DIDs, badges, events | 15 min | `cd multi-agent-demo && ./setup.sh` |

**New to CapiscIO?** Start with the Enforcement Demo — 5 minutes, one API key, and you'll see trust enforcement in action.

---

## Prerequisites

1. **Python 3.11+**
2. **A free CapiscIO account** — sign up at [app.capisc.io](https://app.capisc.io)
3. **API key** — Dashboard → Settings → API Keys
4. **OpenAI API key** *(only for integration demos)*

> **Tip:** Run `./setup.sh` before going offline — it pre-downloads a ~15 MB binary that the demos need.

---

## Enforcement Demo — Zero to Enforcement

**"5 minutes from zero to trust-enforced MCP tools."**

An MCP server with three tools at different trust levels. A trusted agent (with a badge) can call restricted tools; an untrusted agent gets denied. Then we revoke the badge — and even the trusted agent is locked out.

### Setup & run

```bash
cd enforcement-demo
./setup.sh                    # Creates venv, installs deps, downloads binary
                              # Edit .env — add CAPISCIO_API_KEY
source .venv/bin/activate
python run_demo.py
```

> Only two env vars needed: `CAPISCIO_API_KEY` (from dashboard) and `CAPISCIO_SERVER_ID` (set to `auto` to create one automatically).

### What you'll see

| # | Agent | Tool | Result | Why |
|---|-------|------|--------|-----|
| 1 | Trusted (badged) | `get_price` | ✓ ALLOW | Open tool |
| 2 | Trusted (badged) | `place_order` | ✓ ALLOW | Badge proves key ownership |
| 3 | Untrusted (no badge) | `get_price` | ✓ ALLOW | Open tool — no badge needed |
| 4 | Untrusted (no badge) | `place_order` | ✗ **DENY** | No badge → trust level too low |
| 5 | Trusted (badge **revoked**) | `place_order` | ✗ **DENY** | Badge revoked in real time |

### Key code

**Server** — one decorator per tool:
```python
@server.tool(min_trust_level=0)    # open to all
async def get_price(sku: str) -> str: ...

@server.tool(min_trust_level=1)    # requires PoP badge
async def place_order(sku: str, quantity: int) -> str: ...
```

**Agent** — one line to connect:
```python
identity = CapiscIO.connect(api_key="sk_live_...", auto_badge=True)
```

**→ Full details, expected output, and troubleshooting: [`enforcement-demo/README.md`](enforcement-demo/README.md)**

---

## MCP Guard Demo

**"Let's Encrypt for MCP servers"** — automatic cryptographic identity, trust badges, and per-tool access control.

| Feature | Description |
|---------|-------------|
| `MCPServerIdentity.connect()` | One-liner: generates keys, registers DID, obtains badge |
| Server identity in `_meta` | Every `initialize` response carries the server's DID + badge |
| Per-tool trust levels | `@server.tool(min_trust_level=N)` — e.g. `list_files`=0, `read_file`=2, `write_file`=3 |
| Client verification | Client validates server DID + badge before calling tools |
| Auto-renewal | `ServerBadgeKeeper` renews the badge before it expires |

### Quick start

```bash
cd mcp-demo
cp .env.example .env            # Set CAPISCIO_SERVER_ID + CAPISCIO_API_KEY
docker compose up --build       # Starts MCP server
docker compose run --rm mcp-client  # Run the client (separate terminal)
```

**→ Full setup, architecture, and expected output: [`mcp-demo/README.md`](mcp-demo/README.md)**

---

## Agent Guard Demos

Run **3 AI agents** built with different frameworks, all secured with CapiscIO trust badges:

- **LangChain** — Research agent with tool calling (port 8001)
- **CrewAI** — Multi-agent crew for creative tasks (port 8002)
- **LangGraph** — Stateful agent with complex workflows (port 8003)

All agents use `CapiscIO.connect()` to get a cryptographic identity (DID), register with the registry, and participate in trusted agent-to-agent communication. Watch their **event logs in real-time** via the [CapiscIO dashboard](https://app.capisc.io).

### Quick Start

### Prerequisites

- Python 3.11+ (3.14+ works but shows deprecation warnings)
- OpenAI API key (or compatible LLM)
- A free CapiscIO account — sign up at [app.capisc.io](https://app.capisc.io)

### 1. Setup agent environments

```bash
cd multi-agent-demo
./setup.sh   # Creates per-agent .venvs, installs deps + shared module
             # Auto-creates .env from .env.example if missing
```

### 2. Configure environment

Edit `multi-agent-demo/.env` with your credentials:
```env
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o-mini

CAPISCIO_SERVER_URL=https://registry.capisc.io
CAPISCIO_API_KEY=sk_live_your_api_key_here
SECURITY_MODE=ca
```

Get your API key from [app.capisc.io](https://app.capisc.io) → Settings → API Keys.

### 3. Run the agents

Each agent needs its own terminal:

```bash
# Terminal 1: LangChain Research Agent
cd multi-agent-demo/agents/langchain-agent
source .venv/bin/activate
python main.py --serve                # port 8001

# Terminal 2: CrewAI Content Crew
cd multi-agent-demo/agents/crewai-agent
source .venv/bin/activate
python main.py --serve                # port 8002

# Terminal 3: LangGraph Support Agent
cd multi-agent-demo/agents/langgraph-agent
source .venv/bin/activate
python main.py --serve                # port 8003
```

Or launch all at once with tmux:
```bash
./run-agents.sh
```

### 4. Run the demo driver

In a new terminal:
```bash
cd multi-agent-demo
source agents/langchain-agent/.venv/bin/activate

# Discover running agents
python run_demo.py --discover

# Send tasks to all agents
python run_demo.py

# Send task to one agent
python run_demo.py --agent langchain

# Custom task
python run_demo.py --agent crewai --task "Write a haiku about trust"

# Multi-agent chain (agents calling each other)
python run_demo.py --chain
```

### 5. Watch events

Open the [CapiscIO dashboard](https://app.capisc.io/events) to see agent registrations, badge issuance, and A2A communication in real-time.

---

### Agent CLI Reference

All agents share the same CLI:

```
python main.py [--serve] [--port PORT]
```

| Flag | Description |
|------|-------------|
| `--serve` | **Required.** Start as HTTP server (A2A protocol) |
| `--port PORT` | Override default port |

Without `--serve`, the agent runs a single interactive task and exits.

Default ports (overridable via env):

| Agent | Default Port | Env Var |
|-------|-------------|---------|
| LangChain | 8001 | `LANGCHAIN_AGENT_PORT` |
| CrewAI | 8002 | `CREWAI_AGENT_PORT` |
| LangGraph | 8003 | `LANGGRAPH_AGENT_PORT` |

### Demo Driver CLI

```
python run_demo.py [OPTIONS]
```

| Flag | Description |
|------|-------------|
| *(no flags)* | Demo all agents sequentially |
| `--discover` | Only fetch Agent Cards, don't send tasks |
| `--agent NAME` | Demo one agent: `langchain`, `crewai`, or `langgraph` |
| `--task "..."` | Custom task text (use with `--agent`) |
| `--chain` | Multi-agent chain demo |

---

### What Happens on Startup

When an agent starts with `--serve`, the SDK (`CapiscIO.connect()`) automatically:

1. **Generates Ed25519 key pair** — Stored in `multi-agent-demo/agents/<name>/.capiscio/keys/`
2. **Derives `did:key` URI** — From the public key (RFC-002 §6.1)
3. **Registers with registry** — Creates agent record via `/v1/sdk/agents`
4. **Patches DID + public key** — Links cryptographic identity to agent
5. **Activates agent** — Sets status to "active"
6. **Starts BadgeKeeper** — Background thread that auto-renews trust badges
7. **Serves A2A endpoints** — Agent Card at `/.well-known/agent.json`, tasks at `/tasks/send`

---

## Project Structure

```
a2a-demos/
├── Makefile                          # Dev/release install & demo commands
├── LICENSE
├── enforcement-demo/                 # Zero to Enforcement (5 min)
│   ├── server/main.py               # MCP server with 3 guarded tools
│   ├── agents/                      # Trusted + untrusted agents
│   ├── run_demo.py                  # 5-scenario orchestrator
│   ├── setup.sh                     # One-command setup
│   ├── .env.example                 # Credential template
│   └── requirements.txt
├── mcp-demo/                        # MCP Guard demo (Docker)
│   ├── server/main.py               # Guarded MCP filesystem server
│   ├── client/main.py               # Client with server verification
│   ├── docker-compose.yml           # Full stack orchestration
│   ├── .env.example                 # Config template
│   └── README.md                    # Detailed MCP demo docs
├── multi-agent-demo/                # Multi-framework agent trust (15 min)
│   ├── agents/
│   │   ├── langchain-agent/         # LangChain research agent (port 8001)
│   │   ├── crewai-agent/            # CrewAI multi-agent crew (port 8002)
│   │   └── langgraph-agent/         # LangGraph stateful agent (port 8003)
│   ├── shared/                      # Shared event emission module
│   ├── run_demo.py                  # Send A2A tasks between agents
│   ├── run-agents.sh                # Launch all 3 agents (tmux or manual)
│   ├── setup.sh                     # Create venvs, install deps
│   └── .env.example                 # Environment template
└── README.md
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│          CapiscIO Registry (registry.capisc.io)          │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────┐      │
│   │ Badge CA │  │ Events   │  │ Agent Registry   │      │
│   │ /v1/badge│  │ /v1/events│  │ /v1/sdk/agents   │      │
│   └──────────┘  └──────────┘  └──────────────────┘      │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
     ┌──────┴──────┐      ┌──────────┴──────────┐
     │Agent Guard  │      │    MCP Guard        │
     ├─────────────┤      ├─────────────────────┤
     │             │      │                     │
     │  LangChain  │      │  MCP Server         │
     │  :8001      │      │  MCPServerIdentity  │
     │             │      │  .connect()         │
     │  CrewAI     │      │  + per-tool trust   │
     │  :8002      │      │        │            │
     │             │      │   stdio│transport   │
     │  LangGraph  │      │        ▼            │
     │  :8003      │      │  MCP Client         │
     │             │      │  verifies server    │
     │ A2A Proto   │      │  DID + badge        │
     └─────────────┘      └─────────────────────┘
```

Each agent gets its own cryptographic identity (DID) and key pair. Badges are CA-signed by the CapiscIO registry.

## Security Configuration

Control badge enforcement via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECURITY_MODE` | `ca` | `ca` for CA-signed badges, `dev` for self-signed |
| `CAPISCIO_REQUIRE_SIGNATURES` | `false` | Require valid badges on incoming A2A requests |
| `CAPISCIO_FAIL_MODE` | `block` | Action on security failure: `block`, `monitor`, or `log` |
| `CAPISCIO_MIN_TRUST_LEVEL` | `0` | Minimum trust level required (0-3) |
| `CAPISCIO_RATE_LIMITING` | `true` | Enable rate limiting |
| `CAPISCIO_RATE_LIMIT_RPM` | `60` | Requests per minute limit |

Example strict configuration:
```env
CAPISCIO_REQUIRE_SIGNATURES=true
CAPISCIO_FAIL_MODE=block
CAPISCIO_MIN_TRUST_LEVEL=1
```

## Event Types

Events visible in the dashboard:

| Event Type | Description |
|------------|-------------|
| `agent.started` | Agent initialized and ready |
| `badge.requested` | Badge requested from CA |
| `badge.renewed` | Badge auto-renewed by keeper |
| `task.started` | A2A task execution began |
| `task.completed` | Task finished successfully |
| `a2a.request` | Outbound A2A call made |
| `a2a.response` | A2A response received |
| `error` | Something went wrong |

## Quick Test

After starting agents, verify everything works:

```bash
# 1. Check all agents are healthy
curl -s http://localhost:8001/health  # LangChain
curl -s http://localhost:8002/health  # CrewAI
curl -s http://localhost:8003/health  # LangGraph

# 2. Discover agent capabilities
python run_demo.py --discover

# 3. Test a single agent (fast - no LLM call)
python run_demo.py --agent langgraph --task "My login is broken"

# Expected output:
# ✅ Task completed in 0.0s
# 📋 Response:
# I understand you're experiencing a technical issue...
```

## 🔧 Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: capiscio binary not found` | Core binary not available | SDK auto-downloads on first run; check network connectivity |
| `ConnectionRefusedError` on agent start | Registry unreachable | Check `CAPISCIO_SERVER_URL` in `.env` and network connectivity |
| `Port 8001 already in use` | Previous agent still running | `lsof -ti:8001 \| xargs kill` |
| Agent starts but no events in dashboard | Wrong API key or server URL | Verify `CAPISCIO_API_KEY` and `CAPISCIO_SERVER_URL` in `.env` |
| `OPENAI_API_KEY not set` | Missing `.env` | `cp .env.example .env` and fill in key |
| `ModuleNotFoundError: capiscio_sdk` | SDK not installed in venv | `source .venv/bin/activate && pip install capiscio-sdk` |
| Pydantic V1 deprecation warning | Using Python 3.14+ | Safe to ignore; functionality still works |

## 📚 Learn More

- [CapiscIO Documentation](https://docs.capisc.io)
- [A2A Protocol Specification](https://github.com/google/a2a)
- [RFC-002: Trust Badge Specification](https://github.com/capiscio/capiscio-rfcs)
- [Python SDK Reference](https://docs.capisc.io/sdk/python)

## 📄 License

MIT - See [LICENSE](LICENSE)

---

<p align="center">
  <strong>CapiscIO — The Universal Authority Layer for AI Agents</strong><br/>
  <a href="https://capisc.io">capisc.io</a> · <a href="https://docs.capisc.io">Docs</a> · <a href="https://github.com/capiscio">GitHub</a>
</p>

# CapiscIO Demos

> Working examples of CapiscIO's "Let's Encrypt for AI" approach — cryptographic identity, trust badges, and policy enforcement for **MCP servers** and **A2A agents**.

## Demos at a Glance

| Demo | What it shows | Time | Quick start |
|------|---------------|------|-------------|
| **[Demo One: Zero to Enforcement](#demo-one--zero-to-enforcement)** | `@guard` decorator, trust levels, badge-based access control | 5 min | `cd demo-one && ./setup.sh` |
| **[Demo Two: Policy as Code](#demo-two--policy-as-code)** | Runtime policy changes alter enforcement — no code deploy | 10 min | `cd demo-two && ./setup.sh` |
| **[MCP Guard Demo](#mcp-guard-demo)** | Server identity, per-tool trust, client verification | 5 min | `cd mcp-demo && docker compose up` |
| **[Agent Guard Demos](#agent-guard-demos)** | 3 framework agents with DID, badges, real-time events | 15 min | `./scripts/setup.sh` |

**New to CapiscIO?** Start with Demo One — it takes 5 minutes and shows the core concept.

---

## Prerequisites

- Python 3.11+
- A free CapiscIO account — sign up at [app.capisc.io](https://app.capisc.io)
- API key from Dashboard → Settings → API Keys
- An MCP server registered in the dashboard (for demo-one and demo-two)

> **PyCon attendees:** Run `./setup.sh` at home before the conference. It pre-downloads a ~15 MB binary that the demos need. Conference Wi-Fi is unreliable.

---

## Demo One — Zero to Enforcement

**"5 minutes from zero to trust-enforced MCP tools."**

An MCP server with three tools at different trust levels. A trusted agent (with a badge) can call restricted tools; an untrusted agent (no badge) gets denied.

### What you'll see

| Scenario | Agent | Tool | Trust Level | Result |
|----------|-------|------|-------------|--------|
| 1 | Trusted (DV badge) | `get_price` | 0 (open) | ALLOW |
| 2 | Trusted (DV badge) | `place_order` | 2 (DV+) | ALLOW |
| 3 | Untrusted (no badge) | `get_price` | 0 (open) | ALLOW |
| 4 | Untrusted (no badge) | `place_order` | 2 (DV+) | **DENY** |

### Setup

```bash
cd demo-one
./setup.sh              # Creates venv, installs deps, downloads binary
cp .env.example .env    # Fill in your API key + server ID
```

### Run

```bash
source .venv/bin/activate
python run_demo.py
```

### Key code

**Server** — one decorator per tool:
```python
@server.tool(min_trust_level=0)
async def get_price(sku: str) -> str: ...

@server.tool(min_trust_level=2)
async def place_order(sku: str, quantity: int) -> str: ...

@server.tool(min_trust_level=4)
async def cancel_all_orders() -> str: ...
```

**Agent** — one line to connect:
```python
identity = CapiscIO.connect(api_key=..., auto_badge=True)
```

### Files

```
demo-one/
├── server/main.py          # MCP server with 3 guarded tools
├── agents/
│   ├── trusted_agent.py    # Badged agent (auto_badge=True)
│   └── untrusted_agent.py  # No-badge agent (auto_badge=False)
├── run_demo.py             # Orchestrator: 4 scenarios
├── setup.sh                # Environment setup + binary download
├── .env.example            # Credential template
└── requirements.txt
```

---

## Demo Two — Policy as Code

**"Same code, three different enforcement outcomes — changed by policy, not deploy."**

Shows how org-level policy changes alter trust enforcement at runtime. The presenter switches policies in the dashboard between phases; the same agents and server produce different ALLOW/DENY results.

### Three Phases

**Phase 1 — Baseline** (trust levels as coded)
| Agent | get_price | place_order |
|-------|-----------|-------------|
| Trusted (DV) | ALLOW | ALLOW |
| Untrusted | ALLOW | **DENY** |

**Phase 2 — Lockdown** (global min raised to EV)
| Agent | get_price | place_order |
|-------|-----------|-------------|
| Trusted (DV) | **DENY** | **DENY** |
| Untrusted | **DENY** | **DENY** |

**Phase 3 — Selective** (get_price overridden to require DV)
| Agent | get_price | place_order |
|-------|-----------|-------------|
| Trusted (DV) | ALLOW | ALLOW |
| Untrusted | **DENY** | **DENY** |

### Setup

```bash
cd demo-two
./setup.sh
cp .env.example .env    # Fill in API key, server ID, org ID, admin JWT
```

Create the three policy proposals:
```bash
source .venv/bin/activate
python scripts/setup_policies.py
```

### Run

```bash
python run_demo.py
```

The script pauses between phases so you can switch policies in the dashboard.

### Policy files

```yaml
# policies/lockdown.yaml — emergency response
version: "1"
min_trust_level: "EV"
```

```yaml
# policies/selective.yaml — per-tool override
version: "1"
mcp_tools:
  - tool: "get_price"
    min_trust_level: "DV"
```

### Files

```
demo-two/
├── policies/
│   ├── baseline.yaml       # Default enforcement
│   ├── lockdown.yaml       # Global min = EV (deny all)
│   └── selective.yaml      # get_price overridden to DV
├── scripts/
│   └── setup_policies.py   # Creates policy proposals via admin JWT
├── server/main.py           # Same MCP server as demo-one
├── agents/                  # Same agents as demo-one
├── run_demo.py              # Interactive 3-phase orchestrator
├── setup.sh
├── .env.example
└── requirements.txt
```

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
cd a2a-demos
./scripts/setup.sh   # Creates per-agent .venvs, installs deps + shared module
cp .env.example .env
```

### 2. Configure environment

Edit `.env` with your credentials:
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
cd a2a-demos/agents/langchain-agent
source .venv/bin/activate
python main.py --serve                # port 8001

# Terminal 2: CrewAI Content Crew
cd a2a-demos/agents/crewai-agent
source .venv/bin/activate
python main.py --serve                # port 8002

# Terminal 3: LangGraph Support Agent
cd a2a-demos/agents/langgraph-agent
source .venv/bin/activate
python main.py --serve                # port 8003
```

Or launch all at once with tmux:
```bash
./scripts/run-agents.sh
```

### 4. Run the demo driver

In a new terminal:
```bash
cd a2a-demos
source agents/langchain-agent/.venv/bin/activate

# Discover running agents
python scripts/demo_driver.py --discover

# Send tasks to all agents
python scripts/demo_driver.py

# Send task to one agent
python scripts/demo_driver.py --agent langchain

# Custom task
python scripts/demo_driver.py --agent crewai --task "Write a haiku about trust"

# Multi-agent chain (agents calling each other)
python scripts/demo_driver.py --chain
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
python scripts/demo_driver.py [OPTIONS]
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

1. **Generates Ed25519 key pair** — Stored in `agents/<name>/.capiscio/keys/`
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
├── demo-one/                     # Zero to Enforcement (5 min)
│   ├── server/main.py            # MCP server with 3 guarded tools
│   ├── agents/                   # Trusted + untrusted agents
│   ├── run_demo.py               # 4-scenario orchestrator
│   └── setup.sh                  # One-command setup
├── demo-two/                     # Policy as Code (10 min)
│   ├── policies/                 # 3 YAML policy files
│   ├── scripts/setup_policies.py # Policy creation via admin JWT
│   ├── run_demo.py               # Interactive 3-phase orchestrator
│   └── setup.sh
├── mcp-demo/                     # MCP Guard demo (Docker)
│   ├── server/main.py            # Guarded MCP filesystem server
│   ├── client/main.py            # Client with server verification
│   ├── docker-compose.yml        # Full stack orchestration
│   └── README.md                 # Detailed MCP demo docs
├── agents/
│   ├── langchain-agent/          # LangChain research agent (port 8001)
│   ├── crewai-agent/             # CrewAI multi-agent crew (port 8002)
│   └── langgraph-agent/          # LangGraph stateful agent (port 8003)
├── scripts/
│   ├── setup.sh                  # Create venvs, install deps
│   ├── run-agents.sh             # Launch all 3 agents (tmux or manual)
│   └── demo_driver.py            # Send A2A tasks between agents
├── shared/
│   └── capiscio_events/          # Shared event emission module
├── .env.example                  # Environment template
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
python scripts/demo_driver.py --discover

# 3. Test a single agent (fast - no LLM call)
python scripts/demo_driver.py --agent langgraph --task "My login is broken"

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

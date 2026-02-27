# A2A Agent Demos with CapiscIO Security

> Interactive demos showcasing AI agents built with different frameworks, all secured with CapiscIO trust badges.

## 🎯 What This Demonstrates

Run **3 different AI agents** using different frameworks:
- **LangChain** - Research agent with tool calling (port 8001)
- **CrewAI** - Multi-agent crew for creative tasks (port 8002)
- **LangGraph** - Stateful agent with complex workflows (port 8003)

All agents use the CapiscIO SDK to get a cryptographic identity (DID), register with the CapiscIO registry, and participate in trusted agent-to-agent communication. Watch their **event logs in real-time** via the [CapiscIO dashboard](https://app.capisc.io).

## 🚀 Quick Start

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

## 🏃 Agent CLI Reference

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

## ⚙️ What Happens on Startup

When an agent starts with `--serve`, the SDK (`CapiscIO.connect()`) automatically:

1. **Generates Ed25519 key pair** — Stored in `agents/<name>/.capiscio/keys/`
2. **Derives `did:key` URI** — From the public key (RFC-002 §6.1)
3. **Registers with registry** — Creates agent record via `/v1/sdk/agents`
4. **Patches DID + public key** — Links cryptographic identity to agent
5. **Activates agent** — Sets status to "active"
6. **Starts BadgeKeeper** — Background thread that auto-renews trust badges
7. **Serves A2A endpoints** — Agent Card at `/.well-known/agent.json`, tasks at `/tasks/send`

---

## 📁 Project Structure

```
a2a-demos/
├── agents/
│   ├── langchain-agent/      # LangChain research agent (port 8001)
│   │   ├── main.py           # Agent implementation
│   │   ├── requirements.txt  # Python dependencies
│   │   └── .venv/            # Created by setup.sh
│   ├── crewai-agent/         # CrewAI multi-agent crew (port 8002)
│   └── langgraph-agent/      # LangGraph stateful agent (port 8003)
├── scripts/
│   ├── setup.sh              # Create venvs, install deps
│   ├── run-agents.sh         # Launch all 3 agents (tmux or manual)
│   └── demo_driver.py        # Send A2A tasks between agents
├── shared/
│   └── capiscio_events/      # Shared event emission module
├── .env.example              # Environment template (all vars documented)
└── README.md
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│          CapiscIO Registry (registry.capisc.io)          │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────┐      │
│   │ Badge CA │  │ Events   │  │ Agent Registry   │      │
│   │ /v1/badge│  │ /v1/events│  │ /v1/sdk/agents   │      │
│   └──────────┘  └──────────┘  └──────────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  LangChain   │ │   CrewAI     │ │  LangGraph   │
│  :8001       │ │  :8002       │ │  :8003       │
│              │ │              │ │              │
│ CapiscIO SDK │ │ CapiscIO SDK │ │ CapiscIO SDK │
│ → DID + Keys │ │ → DID + Keys │ │ → DID + Keys │
│ → Badge      │ │ → Badge      │ │ → Badge      │
│ → Events     │ │ → Events     │ │ → Events     │
│              │ │              │ │              │
│  FastAPI +   │ │  FastAPI +   │ │  FastAPI +   │
│  Middleware  │ │  Middleware  │ │  Middleware  │
└──────────────┘ └──────────────┘ └──────────────┘
        │                                │
        └────── A2A Protocol ────────────┘
```

Each agent gets its own cryptographic identity (DID) and key pair. Badges are CA-signed by the CapiscIO registry.

## 🔐 Security Configuration

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

## 📊 Event Types

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

## ✅ Quick Test

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

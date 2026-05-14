# Agent Guard Demos — Multi-Framework Trust

Run 3 AI agents built with different frameworks, all secured with CapiscIO trust badges and communicating via the A2A protocol.

| Agent | Framework | Port | Demo task |
|-------|-----------|------|-----------|
| Research Agent | LangChain | 8001 | Web search + calculation |
| Content Crew | CrewAI | 8002 | Blog post generation |
| Support Agent | LangGraph | 8003 | Customer support workflow |

## Prerequisites

- Python 3.11+
- OpenAI API key (or compatible LLM)
- A free CapiscIO account — [app.capisc.io](https://app.capisc.io)

## Quick Start

```bash
# 1. Setup
./setup.sh                    # Creates per-agent .venvs, installs deps

# 2. Configure
cp .env.example .env          # If setup.sh didn't create it
                              # Edit .env — add OPENAI_API_KEY + CAPISCIO_API_KEY

# 3. Start agents (pick one)
./run-agents.sh               # tmux: all 3 in one session
                              # no tmux: prints manual instructions

# 4. Run the demo driver (separate terminal)
source agents/langchain-agent/.venv/bin/activate
python run_demo.py
```

## What Each Agent Does

**LangChain Research Agent** — Tool-calling agent with web search, calculator, and time lookup. Demonstrates `CapiscioGuard` + `CapiscioCallbackHandler` for 3-line trust enforcement in LangChain.

**CrewAI Content Crew** — Multi-agent crew for creative tasks. Shows CapiscIO badge verification across CrewAI's agent delegation model.

**LangGraph Support Agent** — Stateful customer support workflow. Demonstrates trust enforcement in LangGraph's graph-based execution.

All agents serve an A2A-compliant Agent Card at `/.well-known/agent.json` and accept tasks at `/tasks/send`.

## Demo Driver CLI

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

## Agent CLI

All agents share the same interface:

```
python main.py [--serve] [--port PORT]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--serve` | — | Start as HTTP server (A2A protocol) |
| `--port` | See below | Override default port |

Without `--serve`, the agent runs a single interactive task and exits.

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENAI_API_KEY` | **Yes** | — | Or compatible LLM key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model for all agents |
| `CAPISCIO_API_KEY` | **Yes** | — | From [app.capisc.io](https://app.capisc.io) → Settings → API Keys |
| `CAPISCIO_SERVER_URL` | No | `https://registry.capisc.io` | Registry URL |
| `SECURITY_MODE` | No | `ca` | `ca` for CA-signed badges, `dev` for self-signed |

## Files

```
multi-agent-demo/
├── agents/
│   ├── langchain-agent/     # LangChain research agent (port 8001)
│   ├── crewai-agent/        # CrewAI content crew (port 8002)
│   └── langgraph-agent/     # LangGraph support agent (port 8003)
├── shared/                  # Shared event emission module
├── run_demo.py              # A2A task driver
├── run-agents.sh            # Launch all agents (tmux or manual)
├── setup.sh                 # One-command setup
└── .env.example             # Environment template
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `OPENAI_API_KEY not set` | `cp .env.example .env` and add your key |
| `Port 8001 already in use` | `lsof -ti:8001 \| xargs kill` |
| `ModuleNotFoundError: capiscio_sdk` | `source .venv/bin/activate && pip install capiscio-sdk` |
| Agent starts but no events in dashboard | Verify `CAPISCIO_API_KEY` in `.env` |
| Pydantic V1 deprecation warning | Safe to ignore on Python 3.14+ |

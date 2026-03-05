# a2a-demos - GitHub Copilot Instructions

## ⛔ ABSOLUTE RULES - NO EXCEPTIONS

### 1. ALL WORK VIA PULL REQUESTS
- **NEVER commit directly to `main`.** All changes MUST go through PRs.

### 2. NO WATCH/BLOCKING COMMANDS
- **NEVER run blocking commands** without timeout
- Agent servers must have explicit shutdown mechanisms

---

## 🚨 CRITICAL: Read First

**Before starting work, read the workspace context files:**
1. `../../.context/CURRENT_SPRINT.md`
2. `../../.context/ACTIVE_TASKS.md`
3. `../../.context/SESSION_LOG.md`

---

## Repository Purpose

**a2a-demos** contains interactive demo agents showcasing CapiscIO security with different AI frameworks. These are NOT production code — they're developer-facing demos for documentation, conference talks, and onboarding.

## Architecture

```
a2a-demos/
├── agents/
│   ├── langchain-agent/     # LangChain research agent
│   │   ├── main.py          # Entry point (--serve or --task)
│   │   ├── agent.py         # Agent implementation
│   │   └── requirements.txt
│   ├── crewai-agent/        # CrewAI multi-agent crew
│   │   ├── main.py
│   │   ├── agent.py
│   │   └── requirements.txt
│   └── langgraph-agent/     # LangGraph stateful agent
│       ├── main.py
│       ├── agent.py
│       └── requirements.txt
├── shared/                  # Shared CapiscIO integration code
│   ├── capiscio_wrapper.py  # Common SDK wrapper
│   └── config.py            # Shared configuration
├── scripts/
│   ├── setup.sh             # Install all agent venvs
│   ├── run-agents.sh        # Start all agents
│   └── demo_driver.py       # Automated demo script
├── docker-compose.yml       # Local infrastructure (server, core, postgres)
└── .env                     # Agent credentials (gitignored)
```

## Key Patterns

### CapiscIO SDK Integration

Each agent uses the Python SDK to register identity and emit events:

```python
from capiscio_sdk import CapiscIO

# Let's Encrypt-style setup (v2.4.1+)
capiscio = await CapiscIO.connect(
    agent_id="<uuid>",
    api_key="sk_live_...",
    server_url="https://registry.capisc.io"
)

# Emit events during agent execution
await capiscio.emit("task_started", {"query": "..."})
```

### Each Agent Has Its Own venv

```bash
cd agents/langchain-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running Agents

```bash
# Serve mode (HTTP server for A2A protocol)
python main.py --serve

# Direct task mode
python main.py --task "Research quantum computing"
```

## Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-...
CAPISCIO_API_KEY=sk_live_...

# Per-agent UUIDs (from registry.capisc.io)
LANGCHAIN_AGENT_ID=<uuid>
CREWAI_AGENT_ID=<uuid>
LANGGRAPH_AGENT_ID=<uuid>

# Optional
CAPISCIO_SERVER_URL=https://registry.capisc.io  # Default
```

## Critical Rules

### 1. Don't Break Demo Simplicity
These demos exist to show developers how easy CapiscIO is. Keep the integration code minimal and readable.

### 2. Each Agent Is Independent
Agents share the `shared/` module but each has its own venv and requirements. Don't create cross-agent dependencies.

### 3. Docker Compose Uses Public Registry
The `mcp-demo/docker-compose.yml` uses the public registry at `registry.capisc.io`. The capiscio-server is a private product — never add localhost server instructions to READMEs.

### 4. Credentials Are Gitignored
The `.env` file contains real API keys. Never commit it. Use `.env.example` as template.

## Common Commands

```bash
# Setup all agents
./scripts/setup.sh

# Run demo
python scripts/demo_driver.py --agent langchain

# Start single agent server
cd agents/langchain-agent && source .venv/bin/activate && python main.py --serve

# Start local infrastructure
docker compose up -d
```

# LangChain Agent with CapiscIO Security

A research agent built with LangChain that demonstrates:
- Automatic badge management with BadgeKeeper
- Real-time event emission to CapiscIO dashboard
- A2A-compliant Agent Card
- Tool calling with web search

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../../.env.example .env
# Edit .env with your API keys

# Run the agent
python main.py
```

## What It Does

1. **Registers as an A2A agent** with Agent Card at `/.well-known/agent.json`
2. **Requests a trust badge** from the CapiscIO CA
3. **Auto-renews badges** via BadgeKeeper before expiration
4. **Emits events** visible in the dashboard at [app.capisc.io/events](https://app.capisc.io/events)
5. **Executes research tasks** using LangChain's tool-calling agents

## Events Emitted

- `agent.started` - Agent initialized
- `badge.renewed` - Badge auto-renewed
- `langchain.chain.start` / `langchain.chain.end` - Chain execution
- `langchain.tool.start` / `langchain.tool.end` - Tool invocations
- `task.completed` - Research task finished

# LangGraph Stateful Agent with CapiscIO Security

A stateful workflow agent built with LangGraph that demonstrates:
- Graph-based agent workflows
- State management across nodes
- Event emission for each graph node transition
- A2A-compliant task execution

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../../.env.example .env

# Run the agent
python main.py
```

## The Workflow

This demo implements a customer support workflow:

```
START → classify_request → route_to_handler
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   tech_support        billing_support      general_support
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                      generate_response
                              │
                              ▼
                            END
```

## Events Emitted

- `langgraph.node.start` / `langgraph.node.end` - Node execution
- `langgraph.edge.taken` - Graph transitions
- `langgraph.state.update` - State changes
- `task.completed` - Final output

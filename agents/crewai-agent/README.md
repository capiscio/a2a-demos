# CrewAI Multi-Agent System with CapiscIO Security

A multi-agent crew built with CrewAI that demonstrates:
- Multiple AI agents working together
- Automatic badge management
- Real-time event emission for each agent in the crew
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

# Run the crew
python main.py
```

## The Crew

This demo includes a content creation crew with 3 agents:

1. **Researcher** - Gathers information on a topic
2. **Writer** - Creates content from research
3. **Editor** - Reviews and polishes the content

## Events Emitted

- `crewai.crew.start` / `crewai.crew.end` - Crew execution
- `crewai.agent.start` / `crewai.agent.end` - Individual agent work
- `crewai.task.start` / `crewai.task.end` - Task execution
- `task.completed` - Final output ready

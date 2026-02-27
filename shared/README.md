# CapiscIO Events

Shared event emitter for A2A demos.

## Installation

```bash
pip install -e .
```

## Usage

```python
from capiscio_events import EventEmitter, EventType

emitter = EventEmitter(
    server_url="http://localhost:8080",
    api_key="sk_test_demo_key",
    agent_id="my-agent-uuid",
    agent_name="My Agent",
)

# Emit events
emitter.emit("custom.event", {"key": "value"})
emitter.agent_started({"version": "1.0"})
emitter.task_started("task-123", "research")
emitter.task_completed("task-123", {"result": "success"})
```

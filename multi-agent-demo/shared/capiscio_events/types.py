"""Event type definitions for CapiscIO event emission."""

from enum import Enum


class EventSeverity(str, Enum):
    """Event severity levels matching capiscio-server schema."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Common event types for A2A agent demos."""

    # Agent lifecycle
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_READY = "agent.ready"

    # Badge management
    BADGE_REQUESTED = "badge.requested"
    BADGE_ISSUED = "badge.issued"
    BADGE_RENEWED = "badge.renewed"
    BADGE_EXPIRED = "badge.expired"
    BADGE_ERROR = "badge.error"

    # A2A Task lifecycle (Google A2A protocol)
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELED = "task.canceled"

    # A2A Communication
    A2A_REQUEST_SENT = "a2a.request.sent"
    A2A_REQUEST_RECEIVED = "a2a.request.received"
    A2A_RESPONSE_SENT = "a2a.response.sent"
    A2A_RESPONSE_RECEIVED = "a2a.response.received"

    # Tool/Skill execution
    TOOL_INVOKED = "tool.invoked"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Framework-specific
    LANGCHAIN_CHAIN_START = "langchain.chain.start"
    LANGCHAIN_CHAIN_END = "langchain.chain.end"
    LANGCHAIN_LLM_START = "langchain.llm.start"
    LANGCHAIN_LLM_END = "langchain.llm.end"
    LANGCHAIN_TOOL_START = "langchain.tool.start"
    LANGCHAIN_TOOL_END = "langchain.tool.end"

    CREWAI_CREW_START = "crewai.crew.start"
    CREWAI_CREW_END = "crewai.crew.end"
    CREWAI_AGENT_START = "crewai.agent.start"
    CREWAI_AGENT_END = "crewai.agent.end"
    CREWAI_TASK_START = "crewai.task.start"
    CREWAI_TASK_END = "crewai.task.end"

    LANGGRAPH_NODE_START = "langgraph.node.start"
    LANGGRAPH_NODE_END = "langgraph.node.end"
    LANGGRAPH_EDGE_TAKEN = "langgraph.edge.taken"
    LANGGRAPH_STATE_UPDATE = "langgraph.state.update"

    # Generic
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

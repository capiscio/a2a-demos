"""
Event emitter for sending events to CapiscIO server.

This module handles HTTP communication with the capiscio-server /v1/events endpoint,
providing both sync and async interfaces for event emission.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Union

import httpx

from .types import EventSeverity, EventType

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    Emit events to CapiscIO server for real-time dashboard visibility.
    
    Events are sent to POST /v1/events and appear in the CapiscIO dashboard
    with auto-refresh enabled.
    
    Example:
        emitter = EventEmitter(
            server_url="http://localhost:8080",
            api_key="sk_test_demo_key",
            agent_id="my-agent-uuid"
        )
        
        emitter.emit("agent.started", {"version": "1.0.0"})
        emitter.emit(EventType.TASK_STARTED, {"task_id": "123"}, severity="info")
    """
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        default_trace_id: Optional[str] = None,
    ):
        """
        Initialize the event emitter.
        
        Args:
            server_url: CapiscIO server URL (default: from CAPISCIO_SERVER_URL env)
            api_key: API key for authentication (default: from CAPISCIO_API_KEY env)
            agent_id: Agent UUID for event attribution (default: from CAPISCIO_AGENT_ID env)
            agent_name: Human-readable agent name for payloads
            default_trace_id: Default trace ID for correlation (auto-generated if not provided)
        """
        self.server_url = server_url or os.environ.get("CAPISCIO_SERVER_URL", "http://localhost:8080")
        self.api_key = api_key or os.environ.get("CAPISCIO_API_KEY", "")
        self.agent_id = agent_id or os.environ.get("CAPISCIO_AGENT_ID", str(uuid.uuid4()))
        self.agent_name = agent_name or os.environ.get("CAPISCIO_AGENT_NAME", "unnamed-agent")
        self.default_trace_id = default_trace_id or str(uuid.uuid4())
        
        # HTTP client for sync operations
        # Per RFC-003 §3.1: Registry API keys MUST use X-Capiscio-Registry-Key header
        self._client = httpx.Client(
            base_url=self.server_url,
            headers={
                "X-Capiscio-Registry-Key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        
        # Async client (lazy initialized)
        self._async_client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"EventEmitter initialized for agent {self.agent_name} ({self.agent_id})")
    
    def emit(
        self,
        event_type: Union[str, EventType],
        payload: Optional[dict[str, Any]] = None,
        severity: Union[str, EventSeverity] = EventSeverity.INFO,
        trace_id: Optional[str] = None,
    ) -> bool:
        """
        Emit an event to the CapiscIO server (synchronous).
        
        Args:
            event_type: Type of event (use EventType enum or string)
            payload: Event payload data
            severity: Event severity level
            trace_id: Trace ID for correlation (uses default if not provided)
            
        Returns:
            True if event was accepted, False otherwise
        """
        event = self._build_event(event_type, payload, severity, trace_id)
        
        try:
            response = self._client.post("/v1/events", json=event)
            if response.status_code == 202:
                logger.debug(f"Event emitted: {event_type}")
                return True
            else:
                logger.warning(f"Event rejected: {response.status_code} - {response.text}")
                return False
        except httpx.RequestError as e:
            logger.error(f"Failed to emit event: {e}")
            return False
    
    async def emit_async(
        self,
        event_type: Union[str, EventType],
        payload: Optional[dict[str, Any]] = None,
        severity: Union[str, EventSeverity] = EventSeverity.INFO,
        trace_id: Optional[str] = None,
    ) -> bool:
        """
        Emit an event to the CapiscIO server (asynchronous).
        
        Args:
            event_type: Type of event (use EventType enum or string)
            payload: Event payload data
            severity: Event severity level
            trace_id: Trace ID for correlation (uses default if not provided)
            
        Returns:
            True if event was accepted, False otherwise
        """
        if self._async_client is None:
            # Per RFC-003 §3.1: Registry API keys MUST use X-Capiscio-Registry-Key header
            self._async_client = httpx.AsyncClient(
                base_url=self.server_url,
                headers={
                    "X-Capiscio-Registry-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        
        event = self._build_event(event_type, payload, severity, trace_id)
        
        try:
            response = await self._async_client.post("/v1/events", json=event)
            if response.status_code == 202:
                logger.debug(f"Event emitted: {event_type}")
                return True
            else:
                logger.warning(f"Event rejected: {response.status_code} - {response.text}")
                return False
        except httpx.RequestError as e:
            logger.error(f"Failed to emit event: {e}")
            return False
    
    def _build_event(
        self,
        event_type: Union[str, EventType],
        payload: Optional[dict[str, Any]],
        severity: Union[str, EventSeverity],
        trace_id: Optional[str],
    ) -> dict[str, Any]:
        """Build the event payload matching capiscio-server db.Event schema."""
        
        # Convert enums to strings
        if isinstance(event_type, EventType):
            event_type = event_type.value
        if isinstance(severity, EventSeverity):
            severity = severity.value
        
        # Enrich payload with agent info
        enriched_payload = {
            "agent_name": self.agent_name,
            **(payload or {}),
        }
        
        return {
            "agentId": self.agent_id,
            "traceId": trace_id or self.default_trace_id,
            "eventType": event_type,
            "severity": severity,
            "payload": enriched_payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def new_trace(self) -> str:
        """Generate a new trace ID and set it as the default."""
        self.default_trace_id = str(uuid.uuid4())
        return self.default_trace_id
    
    def child_trace(self, parent_trace: str) -> str:
        """
        Create a child trace ID for nested operations.
        Format: parent_trace_id.child_suffix
        """
        suffix = uuid.uuid4().hex[:8]
        return f"{parent_trace}.{suffix}"
    
    # Convenience methods for common events
    
    def agent_started(self, metadata: Optional[dict] = None) -> bool:
        """Emit agent.started event."""
        return self.emit(EventType.AGENT_STARTED, metadata)
    
    def agent_ready(self, metadata: Optional[dict] = None) -> bool:
        """Emit agent.ready event."""
        return self.emit(EventType.AGENT_READY, metadata)
    
    def agent_stopped(self, metadata: Optional[dict] = None) -> bool:
        """Emit agent.stopped event."""
        return self.emit(EventType.AGENT_STOPPED, metadata)
    
    def badge_renewed(self, jti: str, expires_at: str) -> bool:
        """Emit badge.renewed event."""
        return self.emit(
            EventType.BADGE_RENEWED,
            {"jti": jti, "expires_at": expires_at},
        )
    
    def task_started(self, task_id: str, task_type: str, metadata: Optional[dict] = None) -> bool:
        """Emit task.started event."""
        return self.emit(
            EventType.TASK_STARTED,
            {"task_id": task_id, "task_type": task_type, **(metadata or {})},
        )
    
    def task_completed(self, task_id: str, result: Optional[dict] = None) -> bool:
        """Emit task.completed event."""
        return self.emit(
            EventType.TASK_COMPLETED,
            {"task_id": task_id, "result": result},
        )
    
    def task_failed(self, task_id: str, error: str) -> bool:
        """Emit task.failed event."""
        return self.emit(
            EventType.TASK_FAILED,
            {"task_id": task_id, "error": error},
            severity=EventSeverity.ERROR,
        )
    
    def tool_invoked(self, tool_name: str, args: Optional[dict] = None) -> bool:
        """Emit tool.invoked event."""
        return self.emit(
            EventType.TOOL_INVOKED,
            {"tool_name": tool_name, "args": args},
        )
    
    def tool_completed(self, tool_name: str, result: Any) -> bool:
        """Emit tool.completed event."""
        return self.emit(
            EventType.TOOL_COMPLETED,
            {"tool_name": tool_name, "result": str(result)[:500]},  # Truncate large results
        )
    
    def error(self, message: str, error_type: Optional[str] = None, details: Optional[dict] = None) -> bool:
        """Emit error event."""
        return self.emit(
            EventType.ERROR,
            {"message": message, "error_type": error_type, **(details or {})},
            severity=EventSeverity.ERROR,
        )
    
    def close(self) -> None:
        """Close HTTP clients."""
        self._client.close()
        if self._async_client:
            # Note: For async client, use `await emitter.aclose()` instead
            pass
    
    async def aclose(self) -> None:
        """Close async HTTP client."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
    
    def __enter__(self) -> "EventEmitter":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    async def __aenter__(self) -> "EventEmitter":
        return self
    
    async def __aexit__(self, *args) -> None:
        await self.aclose()

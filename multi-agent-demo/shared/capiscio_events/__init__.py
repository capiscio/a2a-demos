"""
Shared CapiscIO event emitter for A2A demos.

This module provides a simple interface to emit events to the CapiscIO server,
making them visible in the dashboard for real-time monitoring.
"""

from .emitter import EventEmitter
from .types import EventSeverity, EventType

__all__ = ["EventEmitter", "EventSeverity", "EventType"]

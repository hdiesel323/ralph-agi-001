"""Event system for TUI integration with RalphLoop.

Provides an async event bus for real-time communication between
the RalphLoop execution engine and the TUI display.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events emitted by RalphLoop."""

    # Loop lifecycle
    LOOP_STARTED = "loop_started"
    LOOP_STOPPED = "loop_stopped"
    LOOP_PAUSED = "loop_paused"
    LOOP_RESUMED = "loop_resumed"

    # Iteration events
    ITERATION_STARTED = "iteration_started"
    ITERATION_COMPLETED = "iteration_completed"
    ITERATION_FAILED = "iteration_failed"

    # Task events
    TASK_SELECTED = "task_selected"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Agent events
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTION = "agent_action"
    AGENT_RESULT = "agent_result"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"

    # Metrics events
    TOKENS_USED = "tokens_used"
    COST_UPDATED = "cost_updated"
    METRICS_UPDATED = "metrics_updated"

    # Log events
    LOG_MESSAGE = "log_message"
    LOG_ERROR = "log_error"

    # Progress events
    PROGRESS_UPDATED = "progress_updated"


@dataclass
class Event:
    """An event emitted by RalphLoop.

    Attributes:
        type: The type of event.
        timestamp: When the event occurred.
        data: Event-specific data.
    """

    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure timestamp is set."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


# Type for event handlers
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], "asyncio.Future[None]"]


class EventBus:
    """Async event bus for TUI-RalphLoop communication.

    Supports both sync and async handlers. Handlers are called
    in order of registration.
    """

    _instance: Optional[EventBus] = None

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._handlers: dict[EventType, list[EventHandler | AsyncEventHandler]] = {}
        self._all_handlers: list[EventHandler | AsyncEventHandler] = []
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    @classmethod
    def get_instance(cls) -> EventBus:
        """Get the singleton event bus instance."""
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        if cls._instance is not None:
            cls._instance.stop()
        cls._instance = None

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
    ) -> None:
        """Subscribe to a specific event type.

        Args:
            event_type: The type of event to subscribe to.
            handler: Function to call when event occurs.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler | AsyncEventHandler) -> None:
        """Subscribe to all events.

        Args:
            handler: Function to call for any event.
        """
        self._all_handlers.append(handler)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
    ) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: The event type to unsubscribe from.
            handler: The handler to remove.
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def unsubscribe_all(self, handler: EventHandler | AsyncEventHandler) -> None:
        """Unsubscribe from all events.

        Args:
            handler: The handler to remove.
        """
        try:
            self._all_handlers.remove(handler)
        except ValueError:
            pass

    def emit(self, event: Event) -> None:
        """Emit an event (sync version - queues for async processing).

        Args:
            event: The event to emit.
        """
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropping event: {event.type}")

    async def emit_async(self, event: Event) -> None:
        """Emit an event and wait for handlers (async version).

        Args:
            event: The event to emit.
        """
        await self._dispatch(event)

    async def _dispatch(self, event: Event) -> None:
        """Dispatch event to all registered handlers.

        Args:
            event: The event to dispatch.
        """
        handlers = list(self._all_handlers)
        if event.type in self._handlers:
            handlers.extend(self._handlers[event.type])

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    async def start(self) -> None:
        """Start the event processing loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def stop(self) -> None:
        """Stop the event processing loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None


# Convenience functions for emitting common events
def emit_loop_started(total_iterations: int) -> None:
    """Emit loop started event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.LOOP_STARTED,
            data={"total_iterations": total_iterations},
        )
    )


def emit_loop_stopped(reason: str = "completed") -> None:
    """Emit loop stopped event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.LOOP_STOPPED,
            data={"reason": reason},
        )
    )


def emit_iteration_started(iteration: int, task_id: Optional[str] = None) -> None:
    """Emit iteration started event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.ITERATION_STARTED,
            data={"iteration": iteration, "task_id": task_id},
        )
    )


def emit_iteration_completed(
    iteration: int,
    success: bool,
    duration_seconds: float,
    tokens_used: int = 0,
) -> None:
    """Emit iteration completed event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.ITERATION_COMPLETED,
            data={
                "iteration": iteration,
                "success": success,
                "duration_seconds": duration_seconds,
                "tokens_used": tokens_used,
            },
        )
    )


def emit_task_selected(task_id: str, task_name: str) -> None:
    """Emit task selected event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.TASK_SELECTED,
            data={"task_id": task_id, "task_name": task_name},
        )
    )


def emit_task_completed(task_id: str, success: bool) -> None:
    """Emit task completed event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.TASK_COMPLETED,
            data={"task_id": task_id, "success": success},
        )
    )


def emit_agent_thinking(thought: str) -> None:
    """Emit agent thinking event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.AGENT_THINKING,
            data={"thought": thought},
        )
    )


def emit_agent_action(action: str) -> None:
    """Emit agent action event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.AGENT_ACTION,
            data={"action": action},
        )
    )


def emit_tool_called(tool_name: str, args: dict[str, Any]) -> None:
    """Emit tool called event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.TOOL_CALLED,
            data={"tool_name": tool_name, "args": args},
        )
    )


def emit_tool_result(tool_name: str, success: bool, result: str) -> None:
    """Emit tool result event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.TOOL_RESULT,
            data={"tool_name": tool_name, "success": success, "result": result},
        )
    )


def emit_tokens_used(prompt_tokens: int, completion_tokens: int) -> None:
    """Emit tokens used event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.TOKENS_USED,
            data={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        )
    )


def emit_cost_updated(total_cost: float) -> None:
    """Emit cost updated event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.COST_UPDATED,
            data={"total_cost": total_cost},
        )
    )


def emit_log(level: str, message: str) -> None:
    """Emit log message event."""
    event_type = EventType.LOG_ERROR if level == "error" else EventType.LOG_MESSAGE
    EventBus.get_instance().emit(
        Event(
            type=event_type,
            data={"level": level, "message": message},
        )
    )


def emit_progress(task_name: str, progress: float, eta: str = "") -> None:
    """Emit progress updated event."""
    EventBus.get_instance().emit(
        Event(
            type=EventType.PROGRESS_UPDATED,
            data={"task_name": task_name, "progress": progress, "eta": eta},
        )
    )


def emit_metrics_updated(metrics: dict[str, Any]) -> None:
    """Emit full metrics updated event.

    Args:
        metrics: Dictionary containing all current metrics.
    """
    EventBus.get_instance().emit(
        Event(
            type=EventType.METRICS_UPDATED,
            data=metrics,
        )
    )

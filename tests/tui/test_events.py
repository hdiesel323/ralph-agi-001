"""Tests for TUI event system."""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from ralph_agi.tui.events import (
    Event,
    EventBus,
    EventType,
    emit_loop_started,
    emit_loop_stopped,
    emit_iteration_started,
    emit_iteration_completed,
    emit_task_selected,
    emit_task_completed,
    emit_agent_thinking,
    emit_agent_action,
    emit_tool_called,
    emit_tool_result,
    emit_tokens_used,
    emit_cost_updated,
    emit_log,
    emit_progress,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_loop_events_exist(self):
        """Test loop lifecycle events exist."""
        assert EventType.LOOP_STARTED.value == "loop_started"
        assert EventType.LOOP_STOPPED.value == "loop_stopped"
        assert EventType.LOOP_PAUSED.value == "loop_paused"
        assert EventType.LOOP_RESUMED.value == "loop_resumed"

    def test_iteration_events_exist(self):
        """Test iteration events exist."""
        assert EventType.ITERATION_STARTED.value == "iteration_started"
        assert EventType.ITERATION_COMPLETED.value == "iteration_completed"
        assert EventType.ITERATION_FAILED.value == "iteration_failed"

    def test_task_events_exist(self):
        """Test task events exist."""
        assert EventType.TASK_SELECTED.value == "task_selected"
        assert EventType.TASK_STARTED.value == "task_started"
        assert EventType.TASK_COMPLETED.value == "task_completed"
        assert EventType.TASK_FAILED.value == "task_failed"

    def test_agent_events_exist(self):
        """Test agent events exist."""
        assert EventType.AGENT_THINKING.value == "agent_thinking"
        assert EventType.AGENT_ACTION.value == "agent_action"
        assert EventType.AGENT_RESULT.value == "agent_result"
        assert EventType.TOOL_CALLED.value == "tool_called"
        assert EventType.TOOL_RESULT.value == "tool_result"


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(type=EventType.LOOP_STARTED)
        assert event.type == EventType.LOOP_STARTED
        assert isinstance(event.timestamp, datetime)
        assert event.data == {}

    def test_event_with_data(self):
        """Test creating an event with data."""
        event = Event(
            type=EventType.ITERATION_STARTED,
            data={"iteration": 5, "task_id": "T-1"},
        )
        assert event.data["iteration"] == 5
        assert event.data["task_id"] == "T-1"

    def test_event_with_custom_timestamp(self):
        """Test creating an event with custom timestamp."""
        ts = datetime(2025, 1, 1, 12, 0, 0)
        event = Event(type=EventType.LOOP_STARTED, timestamp=ts)
        assert event.timestamp == ts


class TestEventBus:
    """Tests for EventBus class."""

    @pytest.fixture(autouse=True)
    def reset_bus(self):
        """Reset the event bus before each test."""
        EventBus.reset()
        yield
        EventBus.reset()

    def test_singleton_instance(self):
        """Test that get_instance returns singleton."""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()
        assert bus1 is bus2

    def test_subscribe_to_event(self):
        """Test subscribing to a specific event type."""
        bus = EventBus.get_instance()
        handler = MagicMock()
        bus.subscribe(EventType.LOOP_STARTED, handler)
        assert handler in bus._handlers[EventType.LOOP_STARTED]

    def test_subscribe_all(self):
        """Test subscribing to all events."""
        bus = EventBus.get_instance()
        handler = MagicMock()
        bus.subscribe_all(handler)
        assert handler in bus._all_handlers

    def test_unsubscribe(self):
        """Test unsubscribing from an event type."""
        bus = EventBus.get_instance()
        handler = MagicMock()
        bus.subscribe(EventType.LOOP_STARTED, handler)
        bus.unsubscribe(EventType.LOOP_STARTED, handler)
        assert handler not in bus._handlers.get(EventType.LOOP_STARTED, [])

    def test_unsubscribe_all(self):
        """Test unsubscribing from all events."""
        bus = EventBus.get_instance()
        handler = MagicMock()
        bus.subscribe_all(handler)
        bus.unsubscribe_all(handler)
        assert handler not in bus._all_handlers

    @pytest.mark.asyncio
    async def test_emit_async_calls_handler(self):
        """Test that emit_async calls registered handlers."""
        bus = EventBus.get_instance()
        handler = MagicMock()
        bus.subscribe(EventType.LOOP_STARTED, handler)

        event = Event(type=EventType.LOOP_STARTED, data={"test": "data"})
        await bus.emit_async(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_emit_async_calls_async_handler(self):
        """Test that emit_async works with async handlers."""
        bus = EventBus.get_instance()
        handler = AsyncMock()
        bus.subscribe(EventType.ITERATION_STARTED, handler)

        event = Event(type=EventType.ITERATION_STARTED, data={"iteration": 1})
        await bus.emit_async(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_emit_async_calls_all_handlers(self):
        """Test that emit_async calls handlers subscribed to all events."""
        bus = EventBus.get_instance()
        all_handler = MagicMock()
        specific_handler = MagicMock()

        bus.subscribe_all(all_handler)
        bus.subscribe(EventType.TASK_COMPLETED, specific_handler)

        event = Event(type=EventType.TASK_COMPLETED)
        await bus.emit_async(event)

        all_handler.assert_called_once_with(event)
        specific_handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handler_exception_doesnt_crash(self):
        """Test that handler exceptions don't crash the bus."""
        bus = EventBus.get_instance()

        def bad_handler(event):
            raise ValueError("Handler error")

        good_handler = MagicMock()

        bus.subscribe(EventType.LOOP_STARTED, bad_handler)
        bus.subscribe(EventType.LOOP_STARTED, good_handler)

        event = Event(type=EventType.LOOP_STARTED)
        await bus.emit_async(event)

        # Good handler should still be called
        good_handler.assert_called_once_with(event)

    def test_emit_queues_event(self):
        """Test that emit queues events for async processing."""
        bus = EventBus.get_instance()
        event = Event(type=EventType.LOOP_STARTED)
        bus.emit(event)
        assert not bus._queue.empty()

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test starting and stopping the event bus."""
        bus = EventBus.get_instance()
        await bus.start()
        assert bus._running is True
        bus.stop()
        assert bus._running is False


class TestConvenienceFunctions:
    """Tests for convenience emit functions."""

    @pytest.fixture(autouse=True)
    def reset_bus(self):
        """Reset the event bus before each test."""
        EventBus.reset()
        yield
        EventBus.reset()

    def test_emit_loop_started(self):
        """Test emit_loop_started convenience function."""
        bus = EventBus.get_instance()
        emit_loop_started(total_iterations=100)
        event = bus._queue.get_nowait()
        assert event.type == EventType.LOOP_STARTED
        assert event.data["total_iterations"] == 100

    def test_emit_loop_stopped(self):
        """Test emit_loop_stopped convenience function."""
        bus = EventBus.get_instance()
        emit_loop_stopped(reason="user_interrupt")
        event = bus._queue.get_nowait()
        assert event.type == EventType.LOOP_STOPPED
        assert event.data["reason"] == "user_interrupt"

    def test_emit_iteration_started(self):
        """Test emit_iteration_started convenience function."""
        bus = EventBus.get_instance()
        emit_iteration_started(iteration=5, task_id="T-1")
        event = bus._queue.get_nowait()
        assert event.type == EventType.ITERATION_STARTED
        assert event.data["iteration"] == 5
        assert event.data["task_id"] == "T-1"

    def test_emit_iteration_completed(self):
        """Test emit_iteration_completed convenience function."""
        bus = EventBus.get_instance()
        emit_iteration_completed(
            iteration=5,
            success=True,
            duration_seconds=10.5,
            tokens_used=1000,
        )
        event = bus._queue.get_nowait()
        assert event.type == EventType.ITERATION_COMPLETED
        assert event.data["iteration"] == 5
        assert event.data["success"] is True
        assert event.data["duration_seconds"] == 10.5
        assert event.data["tokens_used"] == 1000

    def test_emit_task_selected(self):
        """Test emit_task_selected convenience function."""
        bus = EventBus.get_instance()
        emit_task_selected(task_id="T-1", task_name="Implement feature")
        event = bus._queue.get_nowait()
        assert event.type == EventType.TASK_SELECTED
        assert event.data["task_id"] == "T-1"
        assert event.data["task_name"] == "Implement feature"

    def test_emit_task_completed(self):
        """Test emit_task_completed convenience function."""
        bus = EventBus.get_instance()
        emit_task_completed(task_id="T-1", success=True)
        event = bus._queue.get_nowait()
        assert event.type == EventType.TASK_COMPLETED
        assert event.data["task_id"] == "T-1"
        assert event.data["success"] is True

    def test_emit_agent_thinking(self):
        """Test emit_agent_thinking convenience function."""
        bus = EventBus.get_instance()
        emit_agent_thinking(thought="Analyzing the codebase...")
        event = bus._queue.get_nowait()
        assert event.type == EventType.AGENT_THINKING
        assert event.data["thought"] == "Analyzing the codebase..."

    def test_emit_agent_action(self):
        """Test emit_agent_action convenience function."""
        bus = EventBus.get_instance()
        emit_agent_action(action="Reading file src/main.py")
        event = bus._queue.get_nowait()
        assert event.type == EventType.AGENT_ACTION
        assert event.data["action"] == "Reading file src/main.py"

    def test_emit_tool_called(self):
        """Test emit_tool_called convenience function."""
        bus = EventBus.get_instance()
        emit_tool_called(tool_name="read_file", args={"path": "test.py"})
        event = bus._queue.get_nowait()
        assert event.type == EventType.TOOL_CALLED
        assert event.data["tool_name"] == "read_file"
        assert event.data["args"]["path"] == "test.py"

    def test_emit_tool_result(self):
        """Test emit_tool_result convenience function."""
        bus = EventBus.get_instance()
        emit_tool_result(tool_name="read_file", success=True, result="file contents")
        event = bus._queue.get_nowait()
        assert event.type == EventType.TOOL_RESULT
        assert event.data["tool_name"] == "read_file"
        assert event.data["success"] is True
        assert event.data["result"] == "file contents"

    def test_emit_tokens_used(self):
        """Test emit_tokens_used convenience function."""
        bus = EventBus.get_instance()
        emit_tokens_used(prompt_tokens=500, completion_tokens=300)
        event = bus._queue.get_nowait()
        assert event.type == EventType.TOKENS_USED
        assert event.data["prompt_tokens"] == 500
        assert event.data["completion_tokens"] == 300

    def test_emit_cost_updated(self):
        """Test emit_cost_updated convenience function."""
        bus = EventBus.get_instance()
        emit_cost_updated(total_cost=2.50)
        event = bus._queue.get_nowait()
        assert event.type == EventType.COST_UPDATED
        assert event.data["total_cost"] == 2.50

    def test_emit_log_info(self):
        """Test emit_log for info level."""
        bus = EventBus.get_instance()
        emit_log(level="info", message="Test message")
        event = bus._queue.get_nowait()
        assert event.type == EventType.LOG_MESSAGE
        assert event.data["level"] == "info"
        assert event.data["message"] == "Test message"

    def test_emit_log_error(self):
        """Test emit_log for error level."""
        bus = EventBus.get_instance()
        emit_log(level="error", message="Error occurred")
        event = bus._queue.get_nowait()
        assert event.type == EventType.LOG_ERROR
        assert event.data["level"] == "error"

    def test_emit_progress(self):
        """Test emit_progress convenience function."""
        bus = EventBus.get_instance()
        emit_progress(task_name="Task 1", progress=50.0, eta="5m")
        event = bus._queue.get_nowait()
        assert event.type == EventType.PROGRESS_UPDATED
        assert event.data["task_name"] == "Task 1"
        assert event.data["progress"] == 50.0
        assert event.data["eta"] == "5m"

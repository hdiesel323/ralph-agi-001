"""Tests for lifecycle hooks.

Tests cover:
- Hook configuration
- Individual hook behaviors
- Custom handler registration
- Error handling
- Session statistics
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.memory.hooks import (
    HookConfig,
    HookContext,
    HookEvent,
    HookResult,
    LifecycleHooks,
)
from ralph_agi.memory.store import MemoryFrame


# Fixtures


@pytest.fixture
def mock_memory_store():
    """Create a mock MemoryStore."""
    store = MagicMock()
    store.get_by_session.return_value = []
    store.get_by_type.return_value = []
    store.get_recent.return_value = []
    store.append.return_value = "frame-123"
    return store


@pytest.fixture
def hooks(mock_memory_store):
    """Create LifecycleHooks with default config."""
    return LifecycleHooks(mock_memory_store)


@pytest.fixture
def hooks_disabled(mock_memory_store):
    """Create LifecycleHooks with hooks disabled."""
    config = HookConfig(enabled=False)
    return LifecycleHooks(mock_memory_store, config)


@pytest.fixture
def custom_config():
    """Create a custom hook config."""
    return HookConfig(
        enabled=True,
        on_iteration_start=True,
        on_iteration_end=True,
        on_error=True,
        on_completion=True,
        context_frames=20,
        max_error_context=1000,
    )


def make_frame(
    frame_id: str = "frame-1",
    frame_type: str = "iteration_result",
    content: str = "Test content",
) -> MemoryFrame:
    """Helper to create test frames."""
    return MemoryFrame(
        id=frame_id,
        content=content,
        frame_type=frame_type,
        metadata={},
        timestamp=datetime.now(timezone.utc).isoformat(),
        tags=[frame_type],
    )


# HookConfig Tests


class TestHookConfig:
    """Tests for HookConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HookConfig()

        assert config.enabled is True
        assert config.on_iteration_start is True
        assert config.on_iteration_end is True
        assert config.on_error is True
        assert config.on_completion is True
        assert config.context_frames == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = HookConfig(
            enabled=False,
            context_frames=50,
            max_error_context=5000,
        )

        assert config.enabled is False
        assert config.context_frames == 50
        assert config.max_error_context == 5000


# HookEvent Tests


class TestHookEvent:
    """Tests for HookEvent enum."""

    def test_events_exist(self):
        """Test all events exist."""
        assert HookEvent.ITERATION_START
        assert HookEvent.ITERATION_END
        assert HookEvent.ERROR
        assert HookEvent.COMPLETION

    def test_event_values(self):
        """Test event values."""
        assert HookEvent.ITERATION_START.value == "iteration_start"
        assert HookEvent.ITERATION_END.value == "iteration_end"
        assert HookEvent.ERROR.value == "error"
        assert HookEvent.COMPLETION.value == "completion"


# HookResult Tests


class TestHookResult:
    """Tests for HookResult."""

    def test_result_defaults(self):
        """Test default result values."""
        result = HookResult(success=True)

        assert result.success is True
        assert result.frame_id is None
        assert result.context_loaded == 0
        assert result.error is None

    def test_result_with_values(self):
        """Test result with values."""
        result = HookResult(
            success=True,
            frame_id="frame-123",
            context_loaded=5,
        )

        assert result.frame_id == "frame-123"
        assert result.context_loaded == 5

    def test_result_with_error(self):
        """Test result with error."""
        result = HookResult(
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"


# HookContext Tests


class TestHookContext:
    """Tests for HookContext."""

    def test_context_creation(self):
        """Test creating a hook context."""
        context = HookContext(
            session_id="sess-123",
            iteration=5,
            timestamp="2025-01-01T00:00:00Z",
            event=HookEvent.ITERATION_START,
        )

        assert context.session_id == "sess-123"
        assert context.iteration == 5
        assert context.event == HookEvent.ITERATION_START
        assert context.data == {}

    def test_context_with_data(self):
        """Test context with additional data."""
        context = HookContext(
            session_id="sess-123",
            iteration=5,
            timestamp="2025-01-01T00:00:00Z",
            event=HookEvent.ERROR,
            data={"error_type": "ValueError"},
        )

        assert context.data["error_type"] == "ValueError"


# LifecycleHooks Initialization Tests


class TestLifecycleHooksInit:
    """Tests for LifecycleHooks initialization."""

    def test_init_default(self, mock_memory_store):
        """Test initialization with defaults."""
        hooks = LifecycleHooks(mock_memory_store)

        assert hooks._store is mock_memory_store
        assert hooks.config is not None
        assert hooks.config.enabled is True

    def test_init_with_config(self, mock_memory_store, custom_config):
        """Test initialization with custom config."""
        hooks = LifecycleHooks(mock_memory_store, custom_config)

        assert hooks.config is custom_config
        assert hooks.config.context_frames == 20


# Custom Handler Tests


class TestLifecycleHooksHandlers:
    """Tests for custom handler registration."""

    def test_register_handler(self, hooks):
        """Test registering a custom handler."""
        handler_called = []

        def custom_handler(context):
            handler_called.append(context)

        hooks.register_handler(HookEvent.ITERATION_START, custom_handler)

        # Trigger the hook
        hooks.on_iteration_start("sess-123", 0)

        assert len(handler_called) == 1
        assert handler_called[0].event == HookEvent.ITERATION_START

    def test_unregister_handler(self, hooks):
        """Test unregistering a custom handler."""
        def custom_handler(context):
            pass

        hooks.register_handler(HookEvent.ITERATION_START, custom_handler)
        result = hooks.unregister_handler(HookEvent.ITERATION_START, custom_handler)

        assert result is True

    def test_unregister_handler_not_found(self, hooks):
        """Test unregistering a handler that wasn't registered."""
        def custom_handler(context):
            pass

        result = hooks.unregister_handler(HookEvent.ITERATION_START, custom_handler)

        assert result is False

    def test_handler_error_doesnt_propagate(self, hooks):
        """Test that handler errors don't break the hook."""
        def broken_handler(context):
            raise RuntimeError("Handler failed")

        hooks.register_handler(HookEvent.ITERATION_START, broken_handler)

        # Should not raise
        result = hooks.on_iteration_start("sess-123", 0)

        assert result.success is True

    def test_multiple_handlers(self, hooks):
        """Test multiple handlers for same event."""
        results = []

        def handler1(context):
            results.append("handler1")

        def handler2(context):
            results.append("handler2")

        hooks.register_handler(HookEvent.ITERATION_END, handler1)
        hooks.register_handler(HookEvent.ITERATION_END, handler2)

        hooks.on_iteration_end("sess-123", 0, success=True)

        assert "handler1" in results
        assert "handler2" in results


# on_iteration_start Tests


class TestOnIterationStart:
    """Tests for on_iteration_start hook."""

    def test_start_hook_loads_context(self, hooks, mock_memory_store):
        """Test start hook loads context frames."""
        mock_frames = [make_frame(f"frame-{i}") for i in range(5)]
        mock_memory_store.get_by_session.return_value = mock_frames

        result = hooks.on_iteration_start("sess-123", 0)

        assert result.success is True
        assert result.context_loaded >= 5
        mock_memory_store.get_by_session.assert_called()

    def test_start_hook_disabled(self, hooks_disabled):
        """Test start hook when disabled."""
        result = hooks_disabled.on_iteration_start("sess-123", 0)

        assert result.success is True
        assert result.context_loaded == 0

    def test_start_hook_includes_errors(self, hooks, mock_memory_store):
        """Test start hook includes error frames."""
        session_frames = [make_frame("frame-1")]
        error_frames = [make_frame("error-1", frame_type="error")]

        mock_memory_store.get_by_session.return_value = session_frames
        mock_memory_store.get_by_type.return_value = error_frames

        result = hooks.on_iteration_start("sess-123", 0)

        assert result.success is True
        # Should include both session and error frames
        mock_memory_store.get_by_type.assert_called()

    def test_start_hook_error_handling(self, hooks, mock_memory_store):
        """Test start hook handles errors gracefully."""
        mock_memory_store.get_by_session.side_effect = RuntimeError("DB error")

        result = hooks.on_iteration_start("sess-123", 0)

        assert result.success is False
        assert "DB error" in result.error

    def test_start_hook_with_extra_kwargs(self, hooks, mock_memory_store):
        """Test start hook accepts extra kwargs."""
        result = hooks.on_iteration_start(
            "sess-123",
            0,
            custom_field="value",
        )

        assert result.success is True


# on_iteration_end Tests


class TestOnIterationEnd:
    """Tests for on_iteration_end hook."""

    def test_end_hook_stores_result(self, hooks, mock_memory_store):
        """Test end hook stores iteration result."""
        result = hooks.on_iteration_end(
            "sess-123",
            0,
            success=True,
            output="Task completed",
        )

        assert result.success is True
        assert result.frame_id == "frame-123"
        mock_memory_store.append.assert_called_once()

    def test_end_hook_disabled(self, hooks_disabled):
        """Test end hook when disabled."""
        result = hooks_disabled.on_iteration_end("sess-123", 0, success=True)

        assert result.success is True
        assert result.frame_id is None

    def test_end_hook_failed_iteration(self, hooks, mock_memory_store):
        """Test end hook for failed iteration."""
        result = hooks.on_iteration_end(
            "sess-123",
            0,
            success=False,
            output="Error occurred",
        )

        assert result.success is True
        call_args = mock_memory_store.append.call_args
        assert "failed" in call_args.kwargs["content"]

    def test_end_hook_with_metadata(self, hooks, mock_memory_store):
        """Test end hook includes metadata."""
        hooks.on_iteration_end(
            "sess-123",
            5,
            success=True,
            task_id="task-001",
        )

        call_args = mock_memory_store.append.call_args
        assert call_args.kwargs["metadata"]["iteration"] == 6
        assert call_args.kwargs["metadata"]["task_id"] == "task-001"

    def test_end_hook_error_handling(self, hooks, mock_memory_store):
        """Test end hook handles errors gracefully."""
        mock_memory_store.append.side_effect = RuntimeError("Storage error")

        result = hooks.on_iteration_end("sess-123", 0, success=True)

        assert result.success is False
        assert "Storage error" in result.error


# on_error Tests


class TestOnError:
    """Tests for on_error hook."""

    def test_error_hook_stores_error(self, hooks, mock_memory_store):
        """Test error hook stores error details."""
        error = ValueError("Invalid input")

        result = hooks.on_error(
            "sess-123",
            5,
            error,
        )

        assert result.success is True
        assert result.frame_id == "frame-123"

    def test_error_hook_disabled(self, hooks_disabled):
        """Test error hook when disabled."""
        error = ValueError("Test error")

        result = hooks_disabled.on_error("sess-123", 0, error)

        assert result.success is True
        assert result.frame_id is None

    def test_error_hook_includes_context(self, hooks, mock_memory_store):
        """Test error hook includes error context."""
        error = RuntimeError("Something failed")

        hooks.on_error(
            "sess-123",
            0,
            error,
            error_context="Processing user request",
        )

        call_args = mock_memory_store.append.call_args
        assert "Processing user request" in call_args.kwargs["content"]

    def test_error_hook_truncates_context(self, hooks, mock_memory_store):
        """Test error hook truncates long context."""
        # Use config with small max_error_context
        config = HookConfig(max_error_context=50)
        hooks = LifecycleHooks(mock_memory_store, config)

        error = ValueError("Test error")
        long_context = "A" * 1000

        hooks.on_error(
            "sess-123",
            0,
            error,
            error_context=long_context,
        )

        call_args = mock_memory_store.append.call_args
        assert "..." in call_args.kwargs["content"]

    def test_error_hook_includes_recent_frames(self, hooks, mock_memory_store):
        """Test error hook includes recent activity."""
        recent_frames = [
            make_frame("frame-1", content="Previous action 1"),
            make_frame("frame-2", content="Previous action 2"),
        ]
        mock_memory_store.get_by_session.return_value = recent_frames

        error = RuntimeError("Test error")
        hooks.on_error("sess-123", 0, error)

        call_args = mock_memory_store.append.call_args
        assert "Recent activity" in call_args.kwargs["content"]

    def test_error_hook_critical_importance(self, hooks, mock_memory_store):
        """Test error hook sets critical importance."""
        error = ValueError("Test error")
        hooks.on_error("sess-123", 0, error)

        call_args = mock_memory_store.append.call_args
        assert call_args.kwargs["metadata"]["importance"] == 10

    def test_error_hook_error_handling(self, hooks, mock_memory_store):
        """Test error hook handles its own errors."""
        mock_memory_store.append.side_effect = RuntimeError("Storage error")
        error = ValueError("Original error")

        result = hooks.on_error("sess-123", 0, error)

        assert result.success is False


# on_completion Tests


class TestOnCompletion:
    """Tests for on_completion hook."""

    def test_completion_hook_stores_summary(self, hooks, mock_memory_store):
        """Test completion hook stores summary."""
        result = hooks.on_completion(
            "sess-123",
            10,
            total_iterations=10,
            success=True,
        )

        assert result.success is True
        assert result.frame_id == "frame-123"

    def test_completion_hook_disabled(self, hooks_disabled):
        """Test completion hook when disabled."""
        result = hooks_disabled.on_completion(
            "sess-123",
            10,
            total_iterations=10,
        )

        assert result.success is True
        assert result.frame_id is None

    def test_completion_hook_with_summary(self, hooks, mock_memory_store):
        """Test completion hook includes custom summary."""
        hooks.on_completion(
            "sess-123",
            10,
            total_iterations=10,
            summary="All tasks completed successfully",
        )

        call_args = mock_memory_store.append.call_args
        assert "All tasks completed successfully" in call_args.kwargs["content"]

    def test_completion_hook_counts_errors(self, hooks, mock_memory_store):
        """Test completion hook counts errors."""
        session_frames = [
            make_frame("f1", frame_type="error"),
            make_frame("f2", frame_type="error"),
            make_frame("f3", frame_type="iteration_result"),
        ]
        mock_memory_store.get_by_session.return_value = session_frames

        hooks.on_completion(
            "sess-123",
            10,
            total_iterations=10,
        )

        call_args = mock_memory_store.append.call_args
        assert call_args.kwargs["metadata"]["error_count"] == 2
        assert call_args.kwargs["metadata"]["iteration_count"] == 1

    def test_completion_hook_failed_completion(self, hooks, mock_memory_store):
        """Test completion hook for unsuccessful completion."""
        hooks.on_completion(
            "sess-123",
            10,
            total_iterations=10,
            success=False,
        )

        call_args = mock_memory_store.append.call_args
        assert "ended without completion" in call_args.kwargs["content"]

    def test_completion_hook_error_handling(self, hooks, mock_memory_store):
        """Test completion hook handles errors gracefully."""
        mock_memory_store.append.side_effect = RuntimeError("Storage error")

        result = hooks.on_completion("sess-123", 10, total_iterations=10)

        assert result.success is False


# Session Stats Tests


class TestSessionStats:
    """Tests for session statistics."""

    def test_get_session_stats(self, hooks, mock_memory_store):
        """Test getting session statistics."""
        session_frames = [
            make_frame("f1", frame_type="iteration_result"),
            make_frame("f2", frame_type="iteration_result"),
            make_frame("f3", frame_type="error"),
        ]
        mock_memory_store.get_by_session.return_value = session_frames

        stats = hooks.get_session_stats("sess-123")

        assert stats["session_id"] == "sess-123"
        assert stats["total_frames"] == 3
        assert stats["error_count"] == 1
        assert stats["iteration_count"] == 2

    def test_get_session_stats_empty(self, hooks, mock_memory_store):
        """Test getting stats for empty session."""
        mock_memory_store.get_by_session.return_value = []

        stats = hooks.get_session_stats("sess-123")

        assert stats["total_frames"] == 0
        assert stats["error_count"] == 0

    def test_get_session_stats_error(self, hooks, mock_memory_store):
        """Test getting stats handles errors."""
        mock_memory_store.get_by_session.side_effect = RuntimeError("DB error")

        stats = hooks.get_session_stats("sess-123")

        assert "error" in stats


# Frame Merging Tests


class TestFrameMerging:
    """Tests for frame merging logic."""

    def test_merge_unique_frames(self, hooks):
        """Test merging frames removes duplicates."""
        primary = [
            make_frame("frame-1"),
            make_frame("frame-2"),
        ]
        secondary = [
            make_frame("frame-2"),  # Duplicate
            make_frame("frame-3"),  # New
        ]

        result = hooks._merge_unique_frames(primary, secondary)

        assert len(result) == 3
        ids = [f.id for f in result]
        assert "frame-1" in ids
        assert "frame-2" in ids
        assert "frame-3" in ids

    def test_merge_empty_secondary(self, hooks):
        """Test merging with empty secondary."""
        primary = [make_frame("frame-1")]

        result = hooks._merge_unique_frames(primary, [])

        assert len(result) == 1

    def test_merge_empty_primary(self, hooks):
        """Test merging with empty primary."""
        secondary = [make_frame("frame-1")]

        result = hooks._merge_unique_frames([], secondary)

        assert len(result) == 1


# Integration Tests


class TestLifecycleHooksIntegration:
    """Integration-like tests for hooks workflow."""

    def test_full_iteration_workflow(self, hooks, mock_memory_store):
        """Test full iteration lifecycle."""
        # Start iteration
        start_result = hooks.on_iteration_start("sess-123", 0)
        assert start_result.success is True

        # End iteration
        end_result = hooks.on_iteration_end(
            "sess-123",
            0,
            success=True,
            output="Task done",
        )
        assert end_result.success is True
        assert end_result.frame_id is not None

    def test_error_during_iteration(self, hooks, mock_memory_store):
        """Test error handling during iteration."""
        # Start iteration
        hooks.on_iteration_start("sess-123", 0)

        # Error occurs
        error = RuntimeError("Task failed")
        error_result = hooks.on_error(
            "sess-123",
            0,
            error,
            error_context="Processing task",
        )
        assert error_result.success is True

        # End iteration as failed
        end_result = hooks.on_iteration_end(
            "sess-123",
            0,
            success=False,
        )
        assert end_result.success is True

    def test_completion_after_iterations(self, hooks, mock_memory_store):
        """Test completion after multiple iterations."""
        # Run iterations
        for i in range(5):
            hooks.on_iteration_start("sess-123", i)
            hooks.on_iteration_end("sess-123", i, success=True)

        # Complete
        result = hooks.on_completion(
            "sess-123",
            4,
            total_iterations=5,
            success=True,
            summary="All done",
        )

        assert result.success is True

    def test_selectively_disabled_hooks(self, mock_memory_store):
        """Test selectively disabling hooks."""
        config = HookConfig(
            enabled=True,
            on_iteration_start=False,  # Disabled
            on_iteration_end=True,
            on_error=False,  # Disabled
            on_completion=True,
        )
        hooks = LifecycleHooks(mock_memory_store, config)

        # Start should be no-op
        start_result = hooks.on_iteration_start("sess-123", 0)
        assert start_result.context_loaded == 0

        # End should work
        end_result = hooks.on_iteration_end("sess-123", 0, success=True)
        assert end_result.frame_id is not None

        # Error should be no-op
        error_result = hooks.on_error("sess-123", 0, ValueError("test"))
        assert error_result.frame_id is None

        # Completion should work
        comp_result = hooks.on_completion("sess-123", 0, total_iterations=1)
        assert comp_result.frame_id is not None

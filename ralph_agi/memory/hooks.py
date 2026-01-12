"""Lifecycle hooks for automatic memory capture.

This module provides hooks that fire at key execution points to
automatically populate memory without manual effort.

Design Principles:
- Non-blocking: Hooks should not slow down execution
- Configurable: Each hook can be enabled/disabled
- Error-tolerant: Hook failures don't break the main loop
- Structured: Consistent metadata across hook events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ralph_agi.memory.store import MemoryFrame, MemoryStore

logger = logging.getLogger(__name__)


class HookEvent(Enum):
    """Hook event types."""

    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    ERROR = "error"
    COMPLETION = "completion"


@dataclass
class HookConfig:
    """Configuration for lifecycle hooks.

    Attributes:
        enabled: Master switch for all hooks.
        on_iteration_start: Load context at iteration start.
        on_iteration_end: Store results at iteration end.
        on_error: Store error details when errors occur.
        on_completion: Store summary on task completion.
        context_frames: Number of context frames to load.
        include_errors_in_context: Include error frames in context.
        include_decisions_in_context: Include decision frames in context.
        max_error_context: Max chars of surrounding context for errors.
    """

    enabled: bool = True
    on_iteration_start: bool = True
    on_iteration_end: bool = True
    on_error: bool = True
    on_completion: bool = True
    context_frames: int = 10
    include_errors_in_context: bool = True
    include_decisions_in_context: bool = True
    max_error_context: int = 2000


@dataclass
class HookContext:
    """Context passed to hooks.

    Attributes:
        session_id: Current session identifier.
        iteration: Current iteration number.
        timestamp: When the hook was triggered.
        event: Type of hook event.
        data: Event-specific data.
    """

    session_id: str
    iteration: int
    timestamp: str
    event: HookEvent
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """Result from a hook execution.

    Attributes:
        success: Whether the hook executed successfully.
        frame_id: ID of stored frame (if any).
        context_loaded: Number of context frames loaded (for start hook).
        error: Error message if hook failed.
    """

    success: bool
    frame_id: Optional[str] = None
    context_loaded: int = 0
    error: Optional[str] = None


class LifecycleHooks:
    """Lifecycle hooks for automatic memory capture.

    Provides hooks at key execution points:
    - on_iteration_start: Loads relevant context
    - on_iteration_end: Stores iteration results
    - on_error: Captures error with surrounding context
    - on_completion: Stores completion summary

    Example:
        >>> hooks = LifecycleHooks(memory_store, config)
        >>> # At iteration start
        >>> context = hooks.on_iteration_start(
        ...     session_id="sess-123",
        ...     iteration=1
        ... )
        >>> # At iteration end
        >>> hooks.on_iteration_end(
        ...     session_id="sess-123",
        ...     iteration=1,
        ...     success=True,
        ...     output="Task completed"
        ... )
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        config: Optional[HookConfig] = None,
    ):
        """Initialize lifecycle hooks.

        Args:
            memory_store: The MemoryStore for persistence.
            config: Hook configuration. Uses defaults if not provided.
        """
        self._store = memory_store
        self.config = config or HookConfig()
        self._custom_handlers: dict[HookEvent, list[Callable]] = {
            event: [] for event in HookEvent
        }

    def register_handler(
        self,
        event: HookEvent,
        handler: Callable[[HookContext], None],
    ) -> None:
        """Register a custom handler for a hook event.

        Args:
            event: The event type to handle.
            handler: Callback function receiving HookContext.
        """
        self._custom_handlers[event].append(handler)

    def unregister_handler(
        self,
        event: HookEvent,
        handler: Callable[[HookContext], None],
    ) -> bool:
        """Unregister a custom handler.

        Args:
            event: The event type.
            handler: The handler to remove.

        Returns:
            True if handler was found and removed.
        """
        try:
            self._custom_handlers[event].remove(handler)
            return True
        except ValueError:
            return False

    def _fire_custom_handlers(self, context: HookContext) -> None:
        """Fire all custom handlers for an event.

        Errors in custom handlers are logged but don't propagate.
        """
        for handler in self._custom_handlers[context.event]:
            try:
                handler(context)
            except Exception as e:
                logger.warning(f"Custom hook handler failed: {e}")

    def _create_context(
        self,
        event: HookEvent,
        session_id: str,
        iteration: int,
        data: Optional[dict[str, Any]] = None,
    ) -> HookContext:
        """Create a HookContext for an event."""
        return HookContext(
            session_id=session_id,
            iteration=iteration,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            data=data or {},
        )

    def on_iteration_start(
        self,
        session_id: str,
        iteration: int,
        **kwargs: Any,
    ) -> HookResult:
        """Hook: Called at the start of each iteration.

        Loads relevant context from memory to inform the current task.

        Args:
            session_id: Current session identifier.
            iteration: Current iteration number (0-indexed).
            **kwargs: Additional data to include.

        Returns:
            HookResult with loaded context count.
        """
        if not self.config.enabled or not self.config.on_iteration_start:
            return HookResult(success=True, context_loaded=0)

        context = self._create_context(
            HookEvent.ITERATION_START,
            session_id,
            iteration,
            kwargs,
        )

        try:
            # Load context from memory
            frames = self._store.get_by_session(
                session_id,
                limit=self.config.context_frames,
            )

            # Optionally include errors and decisions from other sessions
            if self.config.include_errors_in_context:
                error_frames = self._store.get_by_type("error", limit=5)
                frames = self._merge_unique_frames(frames, error_frames)

            if self.config.include_decisions_in_context:
                decision_frames = self._store.get_by_type("decision", limit=5)
                frames = self._merge_unique_frames(frames, decision_frames)

            context.data["loaded_frames"] = len(frames)
            context.data["frame_ids"] = [f.id for f in frames]

            # Fire custom handlers
            self._fire_custom_handlers(context)

            logger.debug(f"Iteration start hook loaded {len(frames)} frames")
            return HookResult(success=True, context_loaded=len(frames))

        except Exception as e:
            logger.warning(f"on_iteration_start hook failed: {e}")
            return HookResult(success=False, error=str(e))

    def _merge_unique_frames(
        self,
        primary: list[MemoryFrame],
        secondary: list[MemoryFrame],
    ) -> list[MemoryFrame]:
        """Merge frame lists, avoiding duplicates."""
        seen_ids = {f.id for f in primary}
        result = list(primary)
        for frame in secondary:
            if frame.id not in seen_ids:
                result.append(frame)
                seen_ids.add(frame.id)
        return result

    def on_iteration_end(
        self,
        session_id: str,
        iteration: int,
        success: bool,
        output: Optional[str] = None,
        **kwargs: Any,
    ) -> HookResult:
        """Hook: Called at the end of each iteration.

        Stores the iteration result in memory.

        Args:
            session_id: Current session identifier.
            iteration: Current iteration number (0-indexed).
            success: Whether the iteration succeeded.
            output: Optional output from the iteration.
            **kwargs: Additional metadata.

        Returns:
            HookResult with stored frame ID.
        """
        if not self.config.enabled or not self.config.on_iteration_end:
            return HookResult(success=True)

        context = self._create_context(
            HookEvent.ITERATION_END,
            session_id,
            iteration,
            {"success": success, "output": output, **kwargs},
        )

        try:
            # Build content
            status = "completed successfully" if success else "failed"
            content = f"Iteration {iteration + 1} {status}"
            if output:
                content += f"\n\nOutput:\n{output[:1000]}"

            # Store frame
            frame_id = self._store.append(
                content=content,
                frame_type="iteration_result",
                metadata={
                    "iteration": iteration + 1,
                    "success": success,
                    "has_output": output is not None,
                    "hook": "iteration_end",
                    **kwargs,
                },
                session_id=session_id,
                tags=["iteration", f"iter-{iteration + 1}", "hook:iteration_end"],
            )

            context.data["frame_id"] = frame_id
            self._fire_custom_handlers(context)

            logger.debug(f"Iteration end hook stored frame {frame_id[:8]}")
            return HookResult(success=True, frame_id=frame_id)

        except Exception as e:
            logger.warning(f"on_iteration_end hook failed: {e}")
            return HookResult(success=False, error=str(e))

    def on_error(
        self,
        session_id: str,
        iteration: int,
        error: Exception,
        error_context: Optional[str] = None,
        **kwargs: Any,
    ) -> HookResult:
        """Hook: Called when an error occurs.

        Captures the error with surrounding context for debugging.

        Args:
            session_id: Current session identifier.
            iteration: Current iteration number (0-indexed).
            error: The exception that occurred.
            error_context: Additional context about what was happening.
            **kwargs: Additional metadata.

        Returns:
            HookResult with stored frame ID.
        """
        if not self.config.enabled or not self.config.on_error:
            return HookResult(success=True)

        context = self._create_context(
            HookEvent.ERROR,
            session_id,
            iteration,
            {"error_type": type(error).__name__, "error_message": str(error), **kwargs},
        )

        try:
            # Build content with error details
            error_type = type(error).__name__
            content_parts = [
                f"Error in iteration {iteration + 1}:",
                f"Type: {error_type}",
                f"Message: {str(error)}",
            ]

            if error_context:
                truncated = error_context[:self.config.max_error_context]
                if len(error_context) > self.config.max_error_context:
                    truncated += "..."
                content_parts.append(f"\nContext:\n{truncated}")

            # Include recent frames for debugging
            recent_frames = self._store.get_by_session(session_id, limit=3)
            if recent_frames:
                content_parts.append("\nRecent activity:")
                for frame in recent_frames[:3]:
                    content_parts.append(f"- [{frame.frame_type}] {frame.content[:100]}...")

            content = "\n".join(content_parts)

            # Store frame
            frame_id = self._store.append(
                content=content,
                frame_type="error",
                metadata={
                    "iteration": iteration + 1,
                    "error_type": error_type,
                    "error_message": str(error)[:500],
                    "hook": "error",
                    "importance": 10,  # Critical
                    **kwargs,
                },
                session_id=session_id,
                tags=["error", f"iter-{iteration + 1}", f"error:{error_type}", "hook:error"],
            )

            context.data["frame_id"] = frame_id
            self._fire_custom_handlers(context)

            logger.debug(f"Error hook stored frame {frame_id[:8]}")
            return HookResult(success=True, frame_id=frame_id)

        except Exception as e:
            logger.warning(f"on_error hook failed: {e}")
            return HookResult(success=False, error=str(e))

    def on_completion(
        self,
        session_id: str,
        iteration: int,
        total_iterations: int,
        success: bool = True,
        summary: Optional[str] = None,
        **kwargs: Any,
    ) -> HookResult:
        """Hook: Called when task completes.

        Stores a completion summary with key metrics.

        Args:
            session_id: Current session identifier.
            iteration: Final iteration number (0-indexed).
            total_iterations: Total iterations executed.
            success: Whether completion was successful.
            summary: Optional completion summary.
            **kwargs: Additional metadata.

        Returns:
            HookResult with stored frame ID.
        """
        if not self.config.enabled or not self.config.on_completion:
            return HookResult(success=True)

        context = self._create_context(
            HookEvent.COMPLETION,
            session_id,
            iteration,
            {"total_iterations": total_iterations, "success": success, **kwargs},
        )

        try:
            # Calculate session statistics
            all_frames = self._store.get_by_session(session_id, limit=1000)
            error_count = sum(1 for f in all_frames if f.frame_type == "error")
            iteration_count = sum(1 for f in all_frames if f.frame_type == "iteration_result")

            # Build content
            status = "completed successfully" if success else "ended without completion"
            content_parts = [
                f"Session {status}",
                f"Session ID: {session_id}",
                f"Total iterations: {total_iterations}",
                f"Errors encountered: {error_count}",
            ]

            if summary:
                content_parts.append(f"\nSummary:\n{summary}")

            content = "\n".join(content_parts)

            # Store frame
            frame_id = self._store.append(
                content=content,
                frame_type="summary",
                metadata={
                    "final_iteration": iteration + 1,
                    "total_iterations": total_iterations,
                    "success": success,
                    "error_count": error_count,
                    "iteration_count": iteration_count,
                    "hook": "completion",
                    "importance": 8,  # High importance
                    **kwargs,
                },
                session_id=session_id,
                tags=["completion", "summary", "hook:completion"],
            )

            context.data["frame_id"] = frame_id
            context.data["error_count"] = error_count
            context.data["iteration_count"] = iteration_count
            self._fire_custom_handlers(context)

            logger.debug(f"Completion hook stored frame {frame_id[:8]}")
            return HookResult(success=True, frame_id=frame_id)

        except Exception as e:
            logger.warning(f"on_completion hook failed: {e}")
            return HookResult(success=False, error=str(e))

    def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """Get statistics for a session.

        Args:
            session_id: Session to get stats for.

        Returns:
            Dictionary with session statistics.
        """
        try:
            frames = self._store.get_by_session(session_id, limit=1000)

            type_counts: dict[str, int] = {}
            for frame in frames:
                type_counts[frame.frame_type] = type_counts.get(frame.frame_type, 0) + 1

            return {
                "session_id": session_id,
                "total_frames": len(frames),
                "frame_types": type_counts,
                "error_count": type_counts.get("error", 0),
                "iteration_count": type_counts.get("iteration_result", 0),
            }
        except Exception as e:
            logger.warning(f"Failed to get session stats: {e}")
            return {"session_id": session_id, "error": str(e)}

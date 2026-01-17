"""Terminal User Interface for RALPH-AGI.

A rich, real-time, developer-native TUI built with Textual.
Provides visual monitoring of the RALPH-AGI loop execution.
"""

from ralph_agi.tui.app import RalphTUI
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

__all__ = [
    "RalphTUI",
    "Event",
    "EventBus",
    "EventType",
    "emit_loop_started",
    "emit_loop_stopped",
    "emit_iteration_started",
    "emit_iteration_completed",
    "emit_task_selected",
    "emit_task_completed",
    "emit_agent_thinking",
    "emit_agent_action",
    "emit_tool_called",
    "emit_tool_result",
    "emit_tokens_used",
    "emit_cost_updated",
    "emit_log",
    "emit_progress",
]

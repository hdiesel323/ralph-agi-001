"""FastAPI backend for RALPH-AGI Visual Control Interface.

Provides REST API and WebSocket endpoints for the Kanban board UI.
"""

from ralph_agi.api.app import create_app

__all__ = ["create_app"]

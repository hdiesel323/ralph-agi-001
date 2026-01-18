"""FastAPI application for RALPH-AGI Visual Control Interface.

This module creates the FastAPI application with REST API routes and
WebSocket endpoint for real-time updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ralph_agi.api.dependencies import set_project_root
from ralph_agi.api.routes import tasks_router, queue_router, execution_router
from ralph_agi.tui.events import Event, EventBus, EventType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        if not self.active_connections:
            return

        # Serialize message
        data = json.dumps(message, default=str)

        # Send to all connections
        async with self._lock:
            disconnected = set()
            for connection in self.active_connections:
                try:
                    await connection.send_text(data)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    disconnected.add(connection)

            # Remove failed connections
            self.active_connections -= disconnected


# Global connection manager
manager = ConnectionManager()


def create_event_handler(manager: ConnectionManager):
    """Create an event handler that broadcasts to WebSockets.

    Args:
        manager: WebSocket connection manager.

    Returns:
        Event handler function.
    """
    async def handler(event: Event) -> None:
        """Handle an event from EventBus and broadcast to WebSockets."""
        message = {
            "type": event.type.value,
            "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.now().isoformat(),
            "data": event.data,
        }
        await manager.broadcast(message)

    return handler


def create_app(
    project_root: Optional[Path | str] = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        project_root: Root directory of the RALPH project.
        cors_origins: Allowed CORS origins (default: localhost variants).

    Returns:
        Configured FastAPI application.
    """
    # Set project root for dependencies
    if project_root:
        set_project_root(project_root)

    # Create app
    app = FastAPI(
        title="RALPH-AGI API",
        description="REST API and WebSocket server for RALPH-AGI Visual Control Interface",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure CORS
    if cors_origins is None:
        cors_origins = [
            "http://localhost:5173",  # Vite dev server
            "http://localhost:3000",  # Alternative dev port
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(tasks_router, prefix="/api")
    app.include_router(queue_router, prefix="/api")
    app.include_router(execution_router, prefix="/api")

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates.

        Clients connect here to receive live updates about:
        - Task status changes
        - Execution progress
        - Loop events
        """
        await manager.connect(websocket)

        # Subscribe to EventBus
        event_bus = EventBus.get_instance()
        handler = create_event_handler(manager)
        event_bus.subscribe_all(handler)

        try:
            # Keep connection alive and listen for client messages
            while True:
                try:
                    # Wait for messages from client (ping/pong, commands)
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0,  # Send ping every 30 seconds
                    )

                    # Handle client messages
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            await websocket.send_text(json.dumps({"type": "pong"}))
                    except json.JSONDecodeError:
                        pass

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    try:
                        await websocket.send_text(json.dumps({"type": "ping"}))
                    except Exception:
                        break

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            event_bus.unsubscribe_all(handler)
            await manager.disconnect(websocket)

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy"}

    # Root endpoint
    @app.get("/")
    async def root() -> dict:
        """Root endpoint with API info."""
        return {
            "name": "RALPH-AGI API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "websocket": "/ws",
        }

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    project_root: Optional[Path | str] = None,
    reload: bool = False,
) -> None:
    """Run the FastAPI server with uvicorn.

    Args:
        host: Host to bind to.
        port: Port to bind to.
        project_root: Root directory of the RALPH project.
        reload: Enable auto-reload for development.
    """
    import uvicorn

    # Set project root before starting
    if project_root:
        set_project_root(project_root)

    uvicorn.run(
        "ralph_agi.api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )

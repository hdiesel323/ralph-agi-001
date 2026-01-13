"""MCP (Model Context Protocol) client implementation.

This module provides a Python client for communicating with MCP servers
via the stdio transport, enabling dynamic tool discovery and execution.

MCP uses JSON-RPC 2.0 over stdin/stdout for local process communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)


# JSON-RPC 2.0 constants
JSONRPC_VERSION = "2.0"


class MCPError(Exception):
    """MCP protocol or execution error."""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        data: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data

    def __repr__(self) -> str:
        if self.code is not None:
            return f"MCPError(code={self.code}, message={self.message!r})"
        return f"MCPError(message={self.message!r})"


class MCPTimeoutError(MCPError):
    """MCP operation timed out."""

    def __init__(self, message: str, timeout: float):
        super().__init__(message)
        self.timeout = timeout


class MCPConnectionError(MCPError):
    """MCP connection/transport error."""

    pass


class MCPMessage:
    """Base class for JSON-RPC messages."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        raise NotImplementedError

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class MCPRequest(MCPMessage):
    """JSON-RPC request message."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: str | int | None = field(default_factory=lambda: str(uuid.uuid4())[:8])
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id,
        }
        if self.params:
            d["params"] = self.params
        return d


@dataclass
class MCPNotification(MCPMessage):
    """JSON-RPC notification (no response expected)."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params:
            d["params"] = self.params
        return d


@dataclass
class MCPResponse:
    """JSON-RPC response message."""

    id: str | int | None
    result: Any = None
    error: MCPError | None = None
    jsonrpc: str = JSONRPC_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPResponse:
        """Parse response from JSON dict."""
        error = None
        if "error" in data:
            err_data = data["error"]
            error = MCPError(
                message=err_data.get("message", "Unknown error"),
                code=err_data.get("code"),
                data=err_data.get("data"),
            )
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=error,
            jsonrpc=data.get("jsonrpc", JSONRPC_VERSION),
        )

    def is_error(self) -> bool:
        """Check if response is an error."""
        return self.error is not None

    def raise_for_error(self) -> None:
        """Raise exception if response is an error."""
        if self.error:
            raise self.error


class Transport(ABC):
    """Abstract transport for MCP communication."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    async def send(self, message: MCPMessage) -> None:
        """Send a message."""
        pass

    @abstractmethod
    async def receive(self, timeout: float | None = None) -> dict[str, Any]:
        """Receive a message."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        pass


class StdioTransport(Transport):
    """Stdio transport for local MCP server processes.

    Launches an MCP server as a subprocess and communicates via stdin/stdout
    using newline-delimited JSON-RPC messages.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ):
        """Initialize stdio transport.

        Args:
            command: Command to launch MCP server
            args: Command arguments
            env: Environment variables (merged with current env)
            cwd: Working directory for subprocess
        """
        self.command = command
        self.args = args or []
        self.env = env
        self.cwd = cwd
        self._process: asyncio.subprocess.Process | None = None
        self._read_task: asyncio.Task | None = None
        self._message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Start the MCP server subprocess."""
        if self._process is not None:
            return

        # Build environment with variable expansion
        process_env = os.environ.copy()
        if self.env:
            for key, value in self.env.items():
                # Expand environment variables in values
                process_env[key] = os.path.expandvars(value)

        cmd = [self.command] + self.args
        logger.info(f"Starting MCP server: {' '.join(cmd)}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=self.cwd,
            )
            logger.info(f"MCP server started with PID {self._process.pid}")

            # Start background reader
            self._read_task = asyncio.create_task(self._read_loop())

        except FileNotFoundError:
            raise MCPConnectionError(f"Command not found: {self.command}")
        except PermissionError:
            raise MCPConnectionError(f"Permission denied: {self.command}")
        except Exception as e:
            raise MCPConnectionError(f"Failed to start MCP server: {e}")

    async def _read_loop(self) -> None:
        """Background task to read messages from stdout."""
        assert self._process is not None
        assert self._process.stdout is not None

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    # EOF - process terminated
                    logger.warning("MCP server stdout closed")
                    break

                line_str = line.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    message = json.loads(line_str)
                    await self._message_queue.put(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from MCP server: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in MCP read loop: {e}")

    async def disconnect(self) -> None:
        """Stop the MCP server subprocess."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        if self._process:
            logger.info(f"Stopping MCP server (PID {self._process.pid})")
            try:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("MCP server did not terminate, killing")
                    self._process.kill()
                    await self._process.wait()
            except ProcessLookupError:
                pass  # Already terminated
            self._process = None

    async def send(self, message: MCPMessage) -> None:
        """Send a JSON-RPC message to the server."""
        if self._process is None or self._process.stdin is None:
            raise MCPConnectionError("Not connected to MCP server")

        async with self._lock:
            json_str = message.to_json() + "\n"
            self._process.stdin.write(json_str.encode("utf-8"))
            await self._process.stdin.drain()
            logger.debug(f"Sent: {message.to_json()}")

    async def receive(self, timeout: float | None = None) -> dict[str, Any]:
        """Receive a JSON-RPC message from the server."""
        if self._process is None:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            if timeout is not None:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=timeout,
                )
            else:
                message = await self._message_queue.get()

            logger.debug(f"Received: {json.dumps(message)}")
            return message

        except asyncio.TimeoutError:
            raise MCPTimeoutError(
                f"Timeout waiting for MCP response ({timeout}s)",
                timeout=timeout or 0,
            )

    def is_connected(self) -> bool:
        """Check if the subprocess is running."""
        return (
            self._process is not None
            and self._process.returncode is None
        )


@dataclass
class ServerCapabilities:
    """MCP server capabilities from initialize response."""

    tools: bool = False
    resources: bool = False
    prompts: bool = False
    logging: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerCapabilities:
        """Parse capabilities from initialize response."""
        caps = data.get("capabilities", {})
        return cls(
            tools="tools" in caps,
            resources="resources" in caps,
            prompts="prompts" in caps,
            logging="logging" in caps,
            raw=caps,
        )


@dataclass
class ServerInfo:
    """MCP server information."""

    name: str
    version: str = ""
    capabilities: ServerCapabilities = field(default_factory=ServerCapabilities)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerInfo:
        """Parse server info from initialize response."""
        server_info = data.get("serverInfo", {})
        return cls(
            name=server_info.get("name", "unknown"),
            version=server_info.get("version", ""),
            capabilities=ServerCapabilities.from_dict(data),
        )


class MCPClient:
    """High-level MCP client for tool interaction.

    Manages connection lifecycle, protocol handshake, and request/response
    correlation for communicating with MCP servers.

    Usage:
        async with MCPClient(transport) as client:
            tools = await client.list_tools()
            result = await client.call_tool("read_file", {"path": "/etc/hosts"})
    """

    # MCP protocol version
    PROTOCOL_VERSION = "2024-11-05"

    # Client info
    CLIENT_NAME = "ralph-agi"
    CLIENT_VERSION = "0.1.0"

    def __init__(
        self,
        transport: Transport,
        timeout: float = 30.0,
    ):
        """Initialize MCP client.

        Args:
            transport: Transport instance for communication
            timeout: Default timeout for operations in seconds
        """
        self.transport = transport
        self.timeout = timeout
        self._pending_requests: dict[str | int, asyncio.Future] = {}
        self._server_info: ServerInfo | None = None
        self._initialized = False
        self._receive_task: asyncio.Task | None = None
        self._notification_handlers: dict[str, Callable] = {}

    @property
    def server_info(self) -> ServerInfo | None:
        """Get server information (available after connect)."""
        return self._server_info

    @property
    def is_connected(self) -> bool:
        """Check if client is connected and initialized."""
        return self._initialized and self.transport.is_connected()

    async def connect(self) -> ServerInfo:
        """Connect to MCP server and perform initialization handshake.

        Returns:
            ServerInfo with server name, version, and capabilities
        """
        if self._initialized:
            return self._server_info

        # Connect transport
        await self.transport.connect()

        # Start response handler
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Send initialize request
        init_request = MCPRequest(
            method="initialize",
            params={
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {
                    "roots": {"listChanged": True},
                },
                "clientInfo": {
                    "name": self.CLIENT_NAME,
                    "version": self.CLIENT_VERSION,
                },
            },
        )

        response = await self._send_request(init_request)
        response.raise_for_error()

        self._server_info = ServerInfo.from_dict(response.result or {})
        logger.info(
            f"Connected to MCP server: {self._server_info.name} "
            f"v{self._server_info.version}"
        )

        # Send initialized notification
        await self.transport.send(MCPNotification(method="notifications/initialized"))

        self._initialized = True
        return self._server_info

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        await self.transport.disconnect()
        self._initialized = False
        self._server_info = None
        logger.info("Disconnected from MCP server")

    async def _receive_loop(self) -> None:
        """Background task to handle incoming messages."""
        try:
            while True:
                message = await self.transport.receive()

                # Check if it's a response (has id)
                if "id" in message:
                    msg_id = message["id"]
                    if msg_id in self._pending_requests:
                        future = self._pending_requests.pop(msg_id)
                        if not future.done():
                            future.set_result(MCPResponse.from_dict(message))
                    else:
                        logger.warning(f"Received response for unknown request: {msg_id}")

                # Check if it's a notification (no id, has method)
                elif "method" in message:
                    method = message["method"]
                    if method in self._notification_handlers:
                        try:
                            handler = self._notification_handlers[method]
                            handler(message.get("params", {}))
                        except Exception as e:
                            logger.error(f"Error in notification handler: {e}")

        except asyncio.CancelledError:
            pass
        except MCPConnectionError:
            logger.warning("MCP connection lost")
        except Exception as e:
            logger.error(f"Error in MCP receive loop: {e}")

    async def _send_request(
        self,
        request: MCPRequest,
        timeout: float | None = None,
    ) -> MCPResponse:
        """Send request and wait for response."""
        if timeout is None:
            timeout = self.timeout

        # Create future for response
        future: asyncio.Future[MCPResponse] = asyncio.get_event_loop().create_future()
        self._pending_requests[request.id] = future

        try:
            await self.transport.send(request)

            if timeout is not None:
                response = await asyncio.wait_for(future, timeout=timeout)
            else:
                response = await future

            return response

        except asyncio.TimeoutError:
            self._pending_requests.pop(request.id, None)
            raise MCPTimeoutError(
                f"Timeout waiting for response to {request.method} ({timeout}s)",
                timeout=timeout or 0,
            )
        except asyncio.CancelledError:
            self._pending_requests.pop(request.id, None)
            raise

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server.

        Returns:
            List of tool definitions with name, description, inputSchema
        """
        if not self._initialized:
            raise MCPConnectionError("Client not initialized. Call connect() first.")

        request = MCPRequest(method="tools/list")
        response = await self._send_request(request)
        response.raise_for_error()

        result = response.result or {}
        return result.get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute a tool with the given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments
            timeout: Optional timeout override

        Returns:
            Tool execution result with content
        """
        if not self._initialized:
            raise MCPConnectionError("Client not initialized. Call connect() first.")

        request = MCPRequest(
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )
        response = await self._send_request(request, timeout=timeout)
        response.raise_for_error()

        return response.result or {}

    def on_notification(self, method: str, handler: Callable) -> None:
        """Register handler for notifications.

        Args:
            method: Notification method to handle
            handler: Callback function(params: dict)
        """
        self._notification_handlers[method] = handler

    async def __aenter__(self) -> MCPClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()


class SyncMCPClient:
    """Synchronous wrapper for MCPClient.

    Provides a synchronous API for code that can't use async/await.
    Runs the async client in a background thread with its own event loop.
    """

    def __init__(
        self,
        transport: Transport,
        timeout: float = 30.0,
    ):
        """Initialize sync MCP client.

        Args:
            transport: Transport instance for communication
            timeout: Default timeout for operations
        """
        self._async_client = MCPClient(transport, timeout)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def _run_loop(self) -> None:
        """Run event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure event loop is running."""
        if self._loop is None:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            self._started.wait(timeout=5.0)
        return self._loop

    def _run_async(self, coro):
        """Run coroutine in background event loop."""
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    @property
    def server_info(self) -> ServerInfo | None:
        """Get server information."""
        return self._async_client.server_info

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._async_client.is_connected

    def connect(self) -> ServerInfo:
        """Connect to MCP server."""
        return self._run_async(self._async_client.connect())

    def disconnect(self) -> None:
        """Disconnect from MCP server."""
        self._run_async(self._async_client.disconnect())
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(timeout=2.0)
            self._loop = None
            self._thread = None

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools."""
        return self._run_async(self._async_client.list_tools())

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute a tool."""
        return self._run_async(
            self._async_client.call_tool(name, arguments, timeout)
        )

    def __enter__(self) -> SyncMCPClient:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()

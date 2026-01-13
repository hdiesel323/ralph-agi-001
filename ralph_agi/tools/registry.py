"""Tool registry for dynamic tool discovery.

Provides a unified interface for discovering and accessing tools
across multiple MCP servers with caching support.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ralph_agi.tools.cache import TTLCache
from ralph_agi.tools.mcp import (
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
    StdioTransport,
)
from ralph_agi.tools.schema import ToolNotFoundError, ToolSchema

logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """MCP server connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ToolInfo:
    """Information about a discovered tool.

    Attributes:
        name: Tool identifier
        description: Human-readable description
        server: Name of the MCP server providing this tool
        input_schema: JSON Schema for tool arguments
    """

    name: str
    description: str
    server: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "server": self.server,
            "input_schema": self.input_schema,
        }

    @classmethod
    def from_mcp_tool(cls, tool_data: dict[str, Any], server: str) -> ToolInfo:
        """Create from MCP tools/list response item."""
        return cls(
            name=tool_data.get("name", ""),
            description=tool_data.get("description", ""),
            server=server,
            input_schema=tool_data.get("inputSchema", {}),
        )


@dataclass
class ServerConfig:
    """Configuration for an MCP server.

    Attributes:
        name: Unique server identifier
        command: Command to launch the server
        args: Command arguments
        env: Environment variables
        cwd: Working directory
        enabled: Whether server is enabled
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    enabled: bool = True

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> ServerConfig:
        """Create from config dict."""
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            cwd=data.get("cwd"),
            enabled=data.get("enabled", True),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "cwd": self.cwd,
            "enabled": self.enabled,
        }


@dataclass
class ServerState:
    """Runtime state for an MCP server.

    Attributes:
        config: Server configuration
        status: Current connection status
        client: MCP client instance (if connected)
        error: Last error message (if status is ERROR)
        tool_count: Number of tools discovered
    """

    config: ServerConfig
    status: ServerStatus = ServerStatus.DISCONNECTED
    client: MCPClient | None = None
    error: str | None = None
    tool_count: int = 0

    @property
    def name(self) -> str:
        """Get server name."""
        return self.config.name

    @property
    def is_connected(self) -> bool:
        """Check if server is connected."""
        return self.status == ServerStatus.CONNECTED and self.client is not None


class ToolRegistry:
    """Registry for dynamic tool discovery across MCP servers.

    Manages connections to multiple MCP servers, discovers available tools,
    and provides a unified interface for tool lookup with caching.

    Usage:
        # From config dict
        config = {
            "tools": {
                "mcp_servers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                    }
                },
                "cache_ttl": 300
            }
        }
        registry = ToolRegistry.from_config(config)

        # List all servers
        servers = registry.list_servers()

        # Discover tools (async)
        tools = await registry.list_tools()

        # Get specific tool
        tool = await registry.get_tool("read_file")

        # Force refresh
        await registry.refresh(force=True)

        # Cleanup
        await registry.close()
    """

    # Default cache TTL in seconds (5 minutes)
    DEFAULT_CACHE_TTL = 300.0

    def __init__(
        self,
        servers: list[ServerConfig] | None = None,
        cache_ttl: float = DEFAULT_CACHE_TTL,
        timeout: float = 30.0,
    ):
        """Initialize tool registry.

        Args:
            servers: List of server configurations
            cache_ttl: Tool cache TTL in seconds
            timeout: Default operation timeout
        """
        self._servers: dict[str, ServerState] = {}
        self._cache: TTLCache[list[ToolInfo]] = TTLCache(default_ttl=cache_ttl)
        self._timeout = timeout
        self._lock = asyncio.Lock()

        # Register servers
        for config in servers or []:
            if config.enabled:
                self._servers[config.name] = ServerState(config=config)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ToolRegistry:
        """Create registry from config dictionary.

        Expected config structure:
            tools:
              mcp_servers:
                server_name:
                  command: "..."
                  args: [...]
                  env: {...}
              cache_ttl: 300
              timeout: 30

        Args:
            config: Configuration dictionary

        Returns:
            Configured ToolRegistry
        """
        tools_config = config.get("tools", {})
        servers_config = tools_config.get("mcp_servers", {})

        servers = [
            ServerConfig.from_dict(name, server_data)
            for name, server_data in servers_config.items()
        ]

        return cls(
            servers=servers,
            cache_ttl=tools_config.get("cache_ttl", cls.DEFAULT_CACHE_TTL),
            timeout=tools_config.get("timeout", 30.0),
        )

    def add_server(self, config: ServerConfig) -> None:
        """Add a server to the registry.

        Args:
            config: Server configuration
        """
        if config.enabled:
            self._servers[config.name] = ServerState(config=config)

    def remove_server(self, name: str) -> bool:
        """Remove a server from the registry.

        Args:
            name: Server name

        Returns:
            True if server was removed
        """
        if name in self._servers:
            del self._servers[name]
            self._cache.invalidate(f"tools:{name}")
            return True
        return False

    def list_servers(self) -> list[dict[str, Any]]:
        """List all configured servers with their status.

        Returns:
            List of server info dicts
        """
        return [
            {
                "name": state.name,
                "status": state.status.value,
                "tool_count": state.tool_count,
                "error": state.error,
                "config": state.config.to_dict(),
            }
            for state in self._servers.values()
        ]

    def get_server(self, name: str) -> dict[str, Any] | None:
        """Get info for a specific server.

        Args:
            name: Server name

        Returns:
            Server info dict or None
        """
        state = self._servers.get(name)
        if state is None:
            return None

        return {
            "name": state.name,
            "status": state.status.value,
            "tool_count": state.tool_count,
            "error": state.error,
            "config": state.config.to_dict(),
        }

    async def connect_server(self, name: str) -> bool:
        """Connect to a specific server.

        Args:
            name: Server name

        Returns:
            True if connection successful
        """
        state = self._servers.get(name)
        if state is None:
            logger.error(f"Server not found: {name}")
            return False

        if state.is_connected:
            return True

        async with self._lock:
            return await self._connect_server(state)

    async def _connect_server(self, state: ServerState) -> bool:
        """Internal: Connect to server (must hold lock)."""
        if state.is_connected:
            return True

        config = state.config
        state.status = ServerStatus.CONNECTING
        state.error = None

        try:
            transport = StdioTransport(
                command=config.command,
                args=config.args,
                env=config.env,
                cwd=config.cwd,
            )
            client = MCPClient(transport, timeout=self._timeout)
            await client.connect()

            state.client = client
            state.status = ServerStatus.CONNECTED
            logger.info(f"Connected to MCP server: {state.name}")
            return True

        except MCPConnectionError as e:
            state.status = ServerStatus.ERROR
            state.error = str(e)
            logger.error(f"Failed to connect to {state.name}: {e}")
            return False

        except Exception as e:
            state.status = ServerStatus.ERROR
            state.error = str(e)
            logger.error(f"Unexpected error connecting to {state.name}: {e}")
            return False

    async def disconnect_server(self, name: str) -> bool:
        """Disconnect from a specific server.

        Args:
            name: Server name

        Returns:
            True if disconnection successful
        """
        state = self._servers.get(name)
        if state is None:
            return False

        async with self._lock:
            return await self._disconnect_server(state)

    async def _disconnect_server(self, state: ServerState) -> bool:
        """Internal: Disconnect from server (must hold lock)."""
        if state.client is not None:
            try:
                await state.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from {state.name}: {e}")

            state.client = None

        state.status = ServerStatus.DISCONNECTED
        state.tool_count = 0
        self._cache.invalidate(f"tools:{state.name}")
        logger.info(f"Disconnected from MCP server: {state.name}")
        return True

    async def list_tools(
        self,
        server: str | None = None,
        force_refresh: bool = False,
    ) -> list[ToolInfo]:
        """List available tools.

        Args:
            server: Optional server filter (None for all)
            force_refresh: Bypass cache

        Returns:
            List of ToolInfo objects
        """
        if server is not None:
            # Single server
            return await self._get_server_tools(server, force_refresh)

        # All servers
        all_tools: list[ToolInfo] = []
        for name in self._servers:
            try:
                tools = await self._get_server_tools(name, force_refresh)
                all_tools.extend(tools)
            except Exception as e:
                logger.warning(f"Failed to get tools from {name}: {e}")

        return all_tools

    async def _get_server_tools(
        self,
        server: str,
        force_refresh: bool = False,
    ) -> list[ToolInfo]:
        """Get tools from a specific server with caching."""
        cache_key = f"tools:{server}"

        # Check cache first
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Discover tools
        state = self._servers.get(server)
        if state is None:
            raise ValueError(f"Unknown server: {server}")

        async with self._lock:
            # Double-check cache after acquiring lock
            if not force_refresh:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    return cached

            # Ensure connected
            if not state.is_connected:
                if not await self._connect_server(state):
                    return []

            # Discover tools
            try:
                tools = await self._discover_tools(state)
                state.tool_count = len(tools)
                self._cache.set(cache_key, tools)
                return tools

            except Exception as e:
                logger.error(f"Failed to discover tools from {server}: {e}")
                state.error = str(e)
                return []

    async def _discover_tools(self, state: ServerState) -> list[ToolInfo]:
        """Discover tools from connected server."""
        if state.client is None:
            raise MCPConnectionError(f"Not connected to {state.name}")

        try:
            raw_tools = await state.client.list_tools()
            tools = [
                ToolInfo.from_mcp_tool(tool_data, state.name)
                for tool_data in raw_tools
            ]
            logger.info(f"Discovered {len(tools)} tools from {state.name}")
            return tools

        except MCPTimeoutError:
            logger.error(f"Timeout discovering tools from {state.name}")
            raise

        except MCPError as e:
            logger.error(f"MCP error discovering tools from {state.name}: {e}")
            raise

    async def get_tool(self, name: str) -> ToolInfo | None:
        """Get a specific tool by name.

        Searches all servers for the tool.

        Args:
            name: Tool name

        Returns:
            ToolInfo or None if not found
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool.name == name:
                return tool
        return None

    async def get_schema(
        self,
        tool_name: str,
        raise_if_not_found: bool = True,
    ) -> ToolSchema | None:
        """Get parsed schema for a specific tool.

        Args:
            tool_name: Name of the tool
            raise_if_not_found: If True, raise ToolNotFoundError when not found

        Returns:
            ToolSchema with parsed parameters

        Raises:
            ToolNotFoundError: If tool not found and raise_if_not_found is True
        """
        tool = await self.get_tool(tool_name)

        if tool is None:
            if raise_if_not_found:
                # Get all tool names for suggestions
                all_tools = await self.list_tools()
                available = [t.name for t in all_tools]
                raise ToolNotFoundError(
                    tool_name=tool_name,
                    available_tools=available,
                )
            return None

        return ToolSchema.from_tool_info(
            tool_name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
        )

    async def get_schemas(
        self,
        tool_names: list[str],
    ) -> dict[str, ToolSchema]:
        """Get schemas for multiple tools.

        Args:
            tool_names: List of tool names

        Returns:
            Dict mapping tool name to schema (missing tools omitted)
        """
        schemas = {}
        for name in tool_names:
            schema = await self.get_schema(name, raise_if_not_found=False)
            if schema is not None:
                schemas[name] = schema
        return schemas

    async def refresh(
        self,
        server: str | None = None,
        force: bool = True,
    ) -> dict[str, Any]:
        """Refresh tool cache.

        Args:
            server: Optional server to refresh (None for all)
            force: Force refresh even if cache valid

        Returns:
            Refresh result with counts
        """
        if server is not None:
            # Single server
            self._cache.invalidate(f"tools:{server}")
            tools = await self._get_server_tools(server, force_refresh=force)
            return {
                "servers_refreshed": 1,
                "total_tools": len(tools),
                "servers": {server: len(tools)},
            }

        # All servers
        self._cache.clear()
        result: dict[str, int] = {}

        for name in self._servers:
            try:
                tools = await self._get_server_tools(name, force_refresh=force)
                result[name] = len(tools)
            except Exception as e:
                logger.warning(f"Failed to refresh {name}: {e}")
                result[name] = 0

        return {
            "servers_refreshed": len(result),
            "total_tools": sum(result.values()),
            "servers": result,
        }

    def cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache stats dict
        """
        return self._cache.stats()

    async def close(self) -> None:
        """Close all server connections and cleanup."""
        async with self._lock:
            for state in self._servers.values():
                if state.client is not None:
                    try:
                        await state.client.disconnect()
                    except Exception as e:
                        logger.warning(f"Error closing {state.name}: {e}")
                    state.client = None
                state.status = ServerStatus.DISCONNECTED

        self._cache.clear()
        logger.info("Tool registry closed")

    async def __aenter__(self) -> ToolRegistry:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

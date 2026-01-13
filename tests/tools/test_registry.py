"""Tests for ToolRegistry implementation."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ralph_agi.tools.registry import (
    ServerConfig,
    ServerState,
    ServerStatus,
    ToolInfo,
    ToolRegistry,
)


# =============================================================================
# ToolInfo Tests
# =============================================================================


class TestToolInfo:
    """Tests for ToolInfo dataclass."""

    def test_tool_info_creation(self):
        """Test creating ToolInfo."""
        tool = ToolInfo(
            name="read_file",
            description="Read a file",
            server="filesystem",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )

        assert tool.name == "read_file"
        assert tool.description == "Read a file"
        assert tool.server == "filesystem"
        assert tool.input_schema["type"] == "object"

    def test_tool_info_to_dict(self):
        """Test ToolInfo to_dict."""
        tool = ToolInfo(
            name="test",
            description="Test tool",
            server="test_server",
        )

        d = tool.to_dict()

        assert d["name"] == "test"
        assert d["description"] == "Test tool"
        assert d["server"] == "test_server"
        assert d["input_schema"] == {}

    def test_tool_info_from_mcp_tool(self):
        """Test creating ToolInfo from MCP response."""
        mcp_data = {
            "name": "read_file",
            "description": "Read contents of a file",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }

        tool = ToolInfo.from_mcp_tool(mcp_data, "filesystem")

        assert tool.name == "read_file"
        assert tool.description == "Read contents of a file"
        assert tool.server == "filesystem"
        assert tool.input_schema["type"] == "object"
        assert "path" in tool.input_schema["properties"]

    def test_tool_info_from_mcp_tool_minimal(self):
        """Test creating ToolInfo from minimal MCP response."""
        mcp_data = {"name": "simple_tool"}

        tool = ToolInfo.from_mcp_tool(mcp_data, "server")

        assert tool.name == "simple_tool"
        assert tool.description == ""
        assert tool.input_schema == {}


# =============================================================================
# ServerConfig Tests
# =============================================================================


class TestServerConfig:
    """Tests for ServerConfig dataclass."""

    def test_server_config_creation(self):
        """Test creating ServerConfig."""
        config = ServerConfig(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            env={"NODE_ENV": "production"},
        )

        assert config.name == "filesystem"
        assert config.command == "npx"
        assert config.args[0] == "-y"
        assert config.env["NODE_ENV"] == "production"
        assert config.enabled is True

    def test_server_config_from_dict(self):
        """Test ServerConfig.from_dict."""
        data = {
            "command": "npx",
            "args": ["-y", "server"],
            "env": {"KEY": "value"},
            "cwd": "/home",
            "enabled": False,
        }

        config = ServerConfig.from_dict("test_server", data)

        assert config.name == "test_server"
        assert config.command == "npx"
        assert config.args == ["-y", "server"]
        assert config.env == {"KEY": "value"}
        assert config.cwd == "/home"
        assert config.enabled is False

    def test_server_config_from_dict_minimal(self):
        """Test ServerConfig.from_dict with minimal data."""
        data = {"command": "test"}

        config = ServerConfig.from_dict("minimal", data)

        assert config.name == "minimal"
        assert config.command == "test"
        assert config.args == []
        assert config.env == {}
        assert config.cwd is None
        assert config.enabled is True

    def test_server_config_to_dict(self):
        """Test ServerConfig.to_dict."""
        config = ServerConfig(
            name="test",
            command="cmd",
            args=["arg"],
            env={"K": "V"},
            cwd="/tmp",
        )

        d = config.to_dict()

        assert d["name"] == "test"
        assert d["command"] == "cmd"
        assert d["args"] == ["arg"]
        assert d["env"] == {"K": "V"}
        assert d["cwd"] == "/tmp"


# =============================================================================
# ServerState Tests
# =============================================================================


class TestServerState:
    """Tests for ServerState dataclass."""

    def test_server_state_creation(self):
        """Test creating ServerState."""
        config = ServerConfig(name="test", command="cmd")
        state = ServerState(config=config)

        assert state.name == "test"
        assert state.status == ServerStatus.DISCONNECTED
        assert state.client is None
        assert state.error is None
        assert not state.is_connected

    def test_server_state_connected(self):
        """Test ServerState when connected."""
        config = ServerConfig(name="test", command="cmd")
        mock_client = MagicMock()
        state = ServerState(
            config=config,
            status=ServerStatus.CONNECTED,
            client=mock_client,
        )

        assert state.is_connected


# =============================================================================
# ToolRegistry Initialization Tests
# =============================================================================


class TestToolRegistryInit:
    """Tests for ToolRegistry initialization."""

    def test_registry_init_empty(self):
        """Test creating empty registry."""
        registry = ToolRegistry()

        assert registry.list_servers() == []

    def test_registry_init_with_servers(self):
        """Test creating registry with servers."""
        servers = [
            ServerConfig(name="fs", command="cmd1"),
            ServerConfig(name="git", command="cmd2"),
        ]
        registry = ToolRegistry(servers=servers)

        server_list = registry.list_servers()

        assert len(server_list) == 2
        assert server_list[0]["name"] == "fs"
        assert server_list[1]["name"] == "git"

    def test_registry_init_skips_disabled(self):
        """Test that disabled servers are skipped."""
        servers = [
            ServerConfig(name="enabled", command="cmd", enabled=True),
            ServerConfig(name="disabled", command="cmd", enabled=False),
        ]
        registry = ToolRegistry(servers=servers)

        server_list = registry.list_servers()

        assert len(server_list) == 1
        assert server_list[0]["name"] == "enabled"

    def test_registry_from_config(self):
        """Test creating registry from config dict."""
        config = {
            "tools": {
                "mcp_servers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "server"],
                    },
                    "github": {
                        "command": "npx",
                        "args": ["-y", "github-server"],
                        "env": {"TOKEN": "xxx"},
                    },
                },
                "cache_ttl": 120,
                "timeout": 60,
            }
        }

        registry = ToolRegistry.from_config(config)
        servers = registry.list_servers()

        assert len(servers) == 2
        names = {s["name"] for s in servers}
        assert "filesystem" in names
        assert "github" in names

    def test_registry_from_config_empty(self):
        """Test creating registry from empty config."""
        registry = ToolRegistry.from_config({})

        assert registry.list_servers() == []


# =============================================================================
# ToolRegistry Server Management Tests
# =============================================================================


class TestToolRegistryServerManagement:
    """Tests for server management operations."""

    def test_add_server(self):
        """Test adding a server."""
        registry = ToolRegistry()
        config = ServerConfig(name="new_server", command="cmd")

        registry.add_server(config)

        servers = registry.list_servers()
        assert len(servers) == 1
        assert servers[0]["name"] == "new_server"

    def test_add_server_disabled_ignored(self):
        """Test that disabled servers are not added."""
        registry = ToolRegistry()
        config = ServerConfig(name="disabled", command="cmd", enabled=False)

        registry.add_server(config)

        assert len(registry.list_servers()) == 0

    def test_remove_server(self):
        """Test removing a server."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        result = registry.remove_server("test")

        assert result is True
        assert len(registry.list_servers()) == 0

    def test_remove_server_not_found(self):
        """Test removing non-existent server."""
        registry = ToolRegistry()

        result = registry.remove_server("nonexistent")

        assert result is False

    def test_get_server(self):
        """Test getting specific server info."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        info = registry.get_server("test")

        assert info is not None
        assert info["name"] == "test"
        assert info["status"] == "disconnected"

    def test_get_server_not_found(self):
        """Test getting non-existent server."""
        registry = ToolRegistry()

        info = registry.get_server("nonexistent")

        assert info is None


# =============================================================================
# ToolRegistry Connection Tests
# =============================================================================


class TestToolRegistryConnection:
    """Tests for server connection operations."""

    @pytest.mark.asyncio
    async def test_connect_server_not_found(self):
        """Test connecting to non-existent server."""
        registry = ToolRegistry()

        result = await registry.connect_server("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_connect_server_command_not_found(self):
        """Test connecting with non-existent command."""
        servers = [ServerConfig(name="bad", command="/nonexistent/command")]
        registry = ToolRegistry(servers=servers)

        result = await registry.connect_server("bad")

        assert result is False

        # Check error is recorded
        info = registry.get_server("bad")
        assert info["status"] == "error"
        assert info["error"] is not None

    @pytest.mark.asyncio
    async def test_disconnect_server_not_found(self):
        """Test disconnecting non-existent server."""
        registry = ToolRegistry()

        result = await registry.disconnect_server("nonexistent")

        assert result is False


# =============================================================================
# ToolRegistry Discovery Tests (with mocks)
# =============================================================================


class TestToolRegistryDiscovery:
    """Tests for tool discovery with mocked MCP client."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = AsyncMock()
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.list_tools = AsyncMock(return_value=[
            {
                "name": "read_file",
                "description": "Read a file",
                "inputSchema": {"type": "object"},
            },
            {
                "name": "write_file",
                "description": "Write a file",
                "inputSchema": {"type": "object"},
            },
        ])
        return client

    @pytest.mark.asyncio
    async def test_list_tools_empty_registry(self):
        """Test listing tools from empty registry."""
        registry = ToolRegistry()

        tools = await registry.list_tools()

        assert tools == []

    @pytest.mark.asyncio
    async def test_list_tools_with_cache(self, mock_mcp_client):
        """Test tool list caching."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers, cache_ttl=100)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_mcp_client
            state.status = ServerStatus.CONNECTED

            # First call - hits server
            tools1 = await registry.list_tools(server="test")
            assert len(tools1) == 2
            assert mock_mcp_client.list_tools.call_count == 1

            # Second call - from cache
            tools2 = await registry.list_tools(server="test")
            assert len(tools2) == 2
            assert mock_mcp_client.list_tools.call_count == 1  # No additional call

    @pytest.mark.asyncio
    async def test_list_tools_force_refresh(self, mock_mcp_client):
        """Test force refresh bypasses cache."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers, cache_ttl=100)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_mcp_client
            state.status = ServerStatus.CONNECTED

            # First call
            await registry.list_tools(server="test")
            assert mock_mcp_client.list_tools.call_count == 1

            # Force refresh
            await registry.list_tools(server="test", force_refresh=True)
            assert mock_mcp_client.list_tools.call_count == 2

    @pytest.mark.asyncio
    async def test_list_tools_unknown_server(self):
        """Test listing tools from unknown server."""
        registry = ToolRegistry()

        with pytest.raises(ValueError) as exc_info:
            await registry._get_server_tools("unknown")

        assert "Unknown server" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_tool_found(self, mock_mcp_client):
        """Test getting specific tool."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_mcp_client
            state.status = ServerStatus.CONNECTED

            tool = await registry.get_tool("read_file")

            assert tool is not None
            assert tool.name == "read_file"
            assert tool.server == "test"

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, mock_mcp_client):
        """Test getting non-existent tool."""
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_mcp_client
            state.status = ServerStatus.CONNECTED

            tool = await registry.get_tool("nonexistent_tool")

            assert tool is None


# =============================================================================
# ToolRegistry Refresh Tests
# =============================================================================


class TestToolRegistryRefresh:
    """Tests for cache refresh operations."""

    @pytest.mark.asyncio
    async def test_refresh_single_server(self):
        """Test refreshing single server."""
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[
            {"name": "tool1", "description": "Test"},
        ])

        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            result = await registry.refresh(server="test")

            assert result["servers_refreshed"] == 1
            assert result["total_tools"] == 1
            assert result["servers"]["test"] == 1

    @pytest.mark.asyncio
    async def test_refresh_all_servers(self):
        """Test refreshing all servers."""
        mock_client1 = AsyncMock()
        mock_client1.list_tools = AsyncMock(return_value=[{"name": "t1"}])

        mock_client2 = AsyncMock()
        mock_client2.list_tools = AsyncMock(return_value=[{"name": "t2"}, {"name": "t3"}])

        servers = [
            ServerConfig(name="s1", command="cmd"),
            ServerConfig(name="s2", command="cmd"),
        ]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            registry._servers["s1"].client = mock_client1
            registry._servers["s1"].status = ServerStatus.CONNECTED
            registry._servers["s2"].client = mock_client2
            registry._servers["s2"].status = ServerStatus.CONNECTED

            result = await registry.refresh()

            assert result["servers_refreshed"] == 2
            assert result["total_tools"] == 3


# =============================================================================
# ToolRegistry Cache Stats Tests
# =============================================================================


class TestToolRegistryCacheStats:
    """Tests for cache statistics."""

    def test_cache_stats_empty(self):
        """Test cache stats on empty registry."""
        registry = ToolRegistry()

        stats = registry.cache_stats()

        assert stats["size"] == 0

    @pytest.mark.asyncio
    async def test_cache_stats_with_data(self):
        """Test cache stats after discovery."""
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=[{"name": "t1"}])

        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            await registry.list_tools()

            stats = registry.cache_stats()

            assert stats["size"] == 1
            assert "tools:test" in stats["entries"]


# =============================================================================
# ToolRegistry Lifecycle Tests
# =============================================================================


class TestToolRegistryLifecycle:
    """Tests for registry lifecycle management."""

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing registry."""
        mock_client = AsyncMock()
        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        state = registry._servers["test"]
        state.client = mock_client
        state.status = ServerStatus.CONNECTED

        await registry.close()

        mock_client.disconnect.assert_called_once()
        assert state.status == ServerStatus.DISCONNECTED
        assert state.client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        servers = [ServerConfig(name="test", command="cmd")]

        async with ToolRegistry(servers=servers) as registry:
            assert len(registry.list_servers()) == 1

        # Registry should be closed
        assert registry._cache.size() == 0


# =============================================================================
# ToolRegistry Error Handling Tests
# =============================================================================


class TestToolRegistryErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_discovery_error_recorded(self):
        """Test that discovery errors are recorded."""
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(side_effect=Exception("Discovery failed"))

        servers = [ServerConfig(name="test", command="cmd")]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            state = registry._servers["test"]
            state.client = mock_client
            state.status = ServerStatus.CONNECTED

            tools = await registry._get_server_tools("test")

            assert tools == []
            assert state.error is not None
            assert "Discovery failed" in state.error

    @pytest.mark.asyncio
    async def test_list_tools_continues_on_error(self):
        """Test that list_tools continues after one server fails."""
        mock_client_good = AsyncMock()
        mock_client_good.list_tools = AsyncMock(return_value=[{"name": "good_tool"}])

        mock_client_bad = AsyncMock()
        mock_client_bad.list_tools = AsyncMock(side_effect=Exception("Failed"))

        servers = [
            ServerConfig(name="good", command="cmd"),
            ServerConfig(name="bad", command="cmd"),
        ]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            registry._servers["good"].client = mock_client_good
            registry._servers["good"].status = ServerStatus.CONNECTED
            registry._servers["bad"].client = mock_client_bad
            registry._servers["bad"].status = ServerStatus.CONNECTED

            tools = await registry.list_tools()

            # Should still get tools from good server
            assert len(tools) == 1
            assert tools[0].name == "good_tool"


# =============================================================================
# ToolRegistry Multiple Server Tests
# =============================================================================


class TestToolRegistryMultipleServers:
    """Tests for multi-server scenarios."""

    @pytest.mark.asyncio
    async def test_list_tools_all_servers(self):
        """Test listing tools from all servers."""
        mock_fs = AsyncMock()
        mock_fs.list_tools = AsyncMock(return_value=[
            {"name": "read_file"},
            {"name": "write_file"},
        ])

        mock_git = AsyncMock()
        mock_git.list_tools = AsyncMock(return_value=[
            {"name": "git_status"},
        ])

        servers = [
            ServerConfig(name="filesystem", command="cmd"),
            ServerConfig(name="git", command="cmd"),
        ]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            registry._servers["filesystem"].client = mock_fs
            registry._servers["filesystem"].status = ServerStatus.CONNECTED
            registry._servers["git"].client = mock_git
            registry._servers["git"].status = ServerStatus.CONNECTED

            tools = await registry.list_tools()

            assert len(tools) == 3
            names = {t.name for t in tools}
            assert "read_file" in names
            assert "write_file" in names
            assert "git_status" in names

    @pytest.mark.asyncio
    async def test_filter_by_server(self):
        """Test filtering tools by server."""
        mock_fs = AsyncMock()
        mock_fs.list_tools = AsyncMock(return_value=[{"name": "fs_tool"}])

        servers = [
            ServerConfig(name="filesystem", command="cmd"),
            ServerConfig(name="git", command="cmd"),
        ]
        registry = ToolRegistry(servers=servers)

        with patch.object(registry, "_connect_server", return_value=True):
            registry._servers["filesystem"].client = mock_fs
            registry._servers["filesystem"].status = ServerStatus.CONNECTED

            tools = await registry.list_tools(server="filesystem")

            assert len(tools) == 1
            assert tools[0].name == "fs_tool"
            assert tools[0].server == "filesystem"

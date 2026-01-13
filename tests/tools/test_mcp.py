"""Tests for MCP client implementation."""

from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ralph_agi.tools.mcp import (
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    MCPTimeoutError,
    ServerCapabilities,
    ServerInfo,
    StdioTransport,
    SyncMCPClient,
    JSONRPC_VERSION,
)


# =============================================================================
# MCPMessage Tests
# =============================================================================

class TestMCPRequest:
    """Tests for MCPRequest."""

    def test_request_to_dict_minimal(self):
        """Test request serialization with minimal fields."""
        request = MCPRequest(method="test/method", id="123")
        d = request.to_dict()

        assert d["jsonrpc"] == JSONRPC_VERSION
        assert d["method"] == "test/method"
        assert d["id"] == "123"
        assert "params" not in d  # No params when empty

    def test_request_to_dict_with_params(self):
        """Test request serialization with params."""
        request = MCPRequest(
            method="tools/call",
            params={"name": "read_file", "arguments": {"path": "/etc/hosts"}},
            id="456",
        )
        d = request.to_dict()

        assert d["method"] == "tools/call"
        assert d["params"]["name"] == "read_file"
        assert d["params"]["arguments"]["path"] == "/etc/hosts"

    def test_request_to_json(self):
        """Test JSON serialization."""
        request = MCPRequest(method="test", id="1")
        json_str = request.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["method"] == "test"

    def test_request_auto_generates_id(self):
        """Test that ID is auto-generated."""
        r1 = MCPRequest(method="test")
        r2 = MCPRequest(method="test")

        assert r1.id is not None
        assert r2.id is not None
        assert r1.id != r2.id


class TestMCPNotification:
    """Tests for MCPNotification."""

    def test_notification_to_dict_minimal(self):
        """Test notification serialization without params."""
        notification = MCPNotification(method="notifications/initialized")
        d = notification.to_dict()

        assert d["jsonrpc"] == JSONRPC_VERSION
        assert d["method"] == "notifications/initialized"
        assert "id" not in d  # Notifications have no id
        assert "params" not in d

    def test_notification_to_dict_with_params(self):
        """Test notification serialization with params."""
        notification = MCPNotification(
            method="notifications/progress",
            params={"progress": 50, "total": 100},
        )
        d = notification.to_dict()

        assert d["params"]["progress"] == 50


class TestMCPResponse:
    """Tests for MCPResponse."""

    def test_response_from_dict_success(self):
        """Test parsing successful response."""
        data = {
            "jsonrpc": "2.0",
            "id": "123",
            "result": {"tools": [{"name": "test_tool"}]},
        }
        response = MCPResponse.from_dict(data)

        assert response.id == "123"
        assert response.result["tools"][0]["name"] == "test_tool"
        assert response.error is None
        assert not response.is_error()

    def test_response_from_dict_error(self):
        """Test parsing error response."""
        data = {
            "jsonrpc": "2.0",
            "id": "123",
            "error": {
                "code": -32600,
                "message": "Invalid Request",
                "data": {"details": "missing method"},
            },
        }
        response = MCPResponse.from_dict(data)

        assert response.id == "123"
        assert response.result is None
        assert response.error is not None
        assert response.error.code == -32600
        assert response.error.message == "Invalid Request"
        assert response.error.data["details"] == "missing method"
        assert response.is_error()

    def test_response_raise_for_error(self):
        """Test raise_for_error raises on error response."""
        data = {
            "jsonrpc": "2.0",
            "id": "123",
            "error": {"code": -1, "message": "Test error"},
        }
        response = MCPResponse.from_dict(data)

        with pytest.raises(MCPError) as exc_info:
            response.raise_for_error()

        assert exc_info.value.code == -1
        assert "Test error" in str(exc_info.value)

    def test_response_raise_for_error_noop_on_success(self):
        """Test raise_for_error does nothing on success."""
        data = {"jsonrpc": "2.0", "id": "123", "result": {}}
        response = MCPResponse.from_dict(data)

        response.raise_for_error()  # Should not raise


# =============================================================================
# MCPError Tests
# =============================================================================

class TestMCPError:
    """Tests for MCPError exceptions."""

    def test_mcp_error_basic(self):
        """Test basic MCPError."""
        error = MCPError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.code is None
        assert error.data is None

    def test_mcp_error_with_code(self):
        """Test MCPError with code."""
        error = MCPError("Invalid request", code=-32600)
        assert error.code == -32600
        assert "Invalid request" in repr(error)
        assert "-32600" in repr(error)

    def test_mcp_error_with_data(self):
        """Test MCPError with additional data."""
        error = MCPError("Failed", code=-1, data={"field": "path"})
        assert error.data["field"] == "path"

    def test_mcp_timeout_error(self):
        """Test MCPTimeoutError."""
        error = MCPTimeoutError("Timed out", timeout=30.0)
        assert error.timeout == 30.0
        assert "Timed out" in str(error)

    def test_mcp_connection_error(self):
        """Test MCPConnectionError."""
        error = MCPConnectionError("Connection refused")
        assert "Connection refused" in str(error)


# =============================================================================
# ServerInfo Tests
# =============================================================================

class TestServerInfo:
    """Tests for ServerInfo and ServerCapabilities."""

    def test_server_capabilities_from_dict(self):
        """Test parsing server capabilities."""
        data = {
            "capabilities": {
                "tools": {},
                "resources": {"listChanged": True},
            }
        }
        caps = ServerCapabilities.from_dict(data)

        assert caps.tools is True
        assert caps.resources is True
        assert caps.prompts is False
        assert caps.logging is False

    def test_server_capabilities_empty(self):
        """Test parsing empty capabilities."""
        caps = ServerCapabilities.from_dict({})

        assert caps.tools is False
        assert caps.resources is False

    def test_server_info_from_dict(self):
        """Test parsing server info."""
        data = {
            "serverInfo": {
                "name": "test-server",
                "version": "1.0.0",
            },
            "capabilities": {"tools": {}},
        }
        info = ServerInfo.from_dict(data)

        assert info.name == "test-server"
        assert info.version == "1.0.0"
        assert info.capabilities.tools is True

    def test_server_info_defaults(self):
        """Test server info with missing fields."""
        info = ServerInfo.from_dict({})

        assert info.name == "unknown"
        assert info.version == ""


# =============================================================================
# StdioTransport Tests
# =============================================================================

class TestStdioTransport:
    """Tests for StdioTransport."""

    def test_transport_init(self):
        """Test transport initialization."""
        transport = StdioTransport(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
            env={"TEST_VAR": "value"},
            cwd="/tmp",
        )

        assert transport.command == "npx"
        assert transport.args == ["-y", "@modelcontextprotocol/server-test"]
        assert transport.env == {"TEST_VAR": "value"}
        assert transport.cwd == "/tmp"
        assert not transport.is_connected()

    @pytest.mark.asyncio
    async def test_transport_connect_command_not_found(self):
        """Test connection with non-existent command."""
        transport = StdioTransport(
            command="/nonexistent/command",
            args=[],
        )

        with pytest.raises(MCPConnectionError) as exc_info:
            await transport.connect()

        assert "Command not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transport_not_connected_send_fails(self):
        """Test send fails when not connected."""
        transport = StdioTransport(command="test")
        request = MCPRequest(method="test")

        with pytest.raises(MCPConnectionError) as exc_info:
            await transport.send(request)

        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transport_not_connected_receive_fails(self):
        """Test receive fails when not connected."""
        transport = StdioTransport(command="test")

        with pytest.raises(MCPConnectionError) as exc_info:
            await transport.receive()

        assert "Not connected" in str(exc_info.value)


# =============================================================================
# MockTransport for Client Tests
# =============================================================================

class MockTransport:
    """Mock transport for testing MCPClient."""

    def __init__(self):
        self._connected = False
        self._messages_to_receive: asyncio.Queue = asyncio.Queue()
        self._sent_messages: list[MCPMessage] = []

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    async def send(self, message: MCPMessage):
        if not self._connected:
            raise MCPConnectionError("Not connected")
        self._sent_messages.append(message)

    async def receive(self, timeout: float | None = None):
        if not self._connected:
            raise MCPConnectionError("Not connected")
        try:
            if timeout:
                return await asyncio.wait_for(
                    self._messages_to_receive.get(),
                    timeout=timeout,
                )
            return await self._messages_to_receive.get()
        except asyncio.TimeoutError:
            raise MCPTimeoutError("Timeout", timeout=timeout or 0)

    def is_connected(self):
        return self._connected

    def queue_response(self, response: dict):
        """Queue a response to be received."""
        self._messages_to_receive.put_nowait(response)

    def get_sent(self) -> list[MCPMessage]:
        """Get all sent messages."""
        return self._sent_messages


# =============================================================================
# MCPClient Tests
# =============================================================================

class TestMCPClient:
    """Tests for MCPClient."""

    @pytest.fixture
    def mock_transport(self):
        """Create mock transport."""
        return MockTransport()

    @pytest.fixture
    def client(self, mock_transport):
        """Create client with mock transport."""
        return MCPClient(mock_transport, timeout=5.0)

    @pytest.mark.asyncio
    async def test_client_connect_success(self, client, mock_transport):
        """Test successful connection and initialization."""
        # Queue initialize response
        mock_transport.queue_response({
            "jsonrpc": "2.0",
            "id": None,  # Will be matched by any pending request
            "result": {
                "serverInfo": {"name": "test-server", "version": "1.0"},
                "capabilities": {"tools": {}},
            },
        })

        # Patch to handle request ID matching
        async def receive_with_matching(timeout=None):
            msg = await mock_transport._messages_to_receive.get()
            # Match the ID from the sent request
            if mock_transport._sent_messages:
                last_sent = mock_transport._sent_messages[-1]
                if hasattr(last_sent, 'id'):
                    msg["id"] = last_sent.id
            return msg

        mock_transport.receive = receive_with_matching

        info = await client.connect()

        assert info.name == "test-server"
        assert info.version == "1.0"
        assert info.capabilities.tools is True
        assert client.is_connected

    @pytest.mark.asyncio
    async def test_client_disconnect(self, client, mock_transport):
        """Test disconnect cleanup."""
        mock_transport._connected = True
        client._initialized = True

        await client.disconnect()

        assert not mock_transport.is_connected()
        assert not client.is_connected
        assert client.server_info is None

    @pytest.mark.asyncio
    async def test_client_list_tools_not_initialized(self, client):
        """Test list_tools fails when not initialized."""
        with pytest.raises(MCPConnectionError) as exc_info:
            await client.list_tools()

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_call_tool_not_initialized(self, client):
        """Test call_tool fails when not initialized."""
        with pytest.raises(MCPConnectionError) as exc_info:
            await client.call_tool("test", {})

        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_context_manager(self, mock_transport):
        """Test async context manager."""
        # Queue initialize response
        init_response = {
            "jsonrpc": "2.0",
            "id": "test",
            "result": {"serverInfo": {"name": "test"}, "capabilities": {}},
        }

        call_count = 0

        async def receive_init(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call is for initialize
                msg = init_response.copy()
                if mock_transport._sent_messages:
                    msg["id"] = mock_transport._sent_messages[-1].id
                return msg
            # Subsequent calls block until cancelled
            await asyncio.sleep(10)
            raise asyncio.CancelledError()

        mock_transport.receive = receive_init

        async with MCPClient(mock_transport, timeout=1.0) as client:
            assert client.is_connected

        assert not mock_transport.is_connected()


# =============================================================================
# SyncMCPClient Tests
# =============================================================================

class TestSyncMCPClient:
    """Tests for synchronous MCP client wrapper."""

    def test_sync_client_init(self):
        """Test sync client initialization."""
        transport = MockTransport()
        client = SyncMCPClient(transport, timeout=10.0)

        assert client._async_client is not None
        assert not client.is_connected

    def test_sync_client_properties(self):
        """Test sync client property forwarding."""
        transport = MockTransport()
        client = SyncMCPClient(transport)

        assert client.server_info is None
        assert not client.is_connected


# =============================================================================
# Integration Tests (with real subprocess)
# =============================================================================

class TestMCPIntegration:
    """Integration tests with actual MCP servers.

    These tests require MCP servers to be installed.
    They are skipped if the required commands are not available.
    """

    @pytest.fixture
    def echo_server_available(self):
        """Check if echo server is available."""
        import shutil
        return shutil.which("npx") is not None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires npx and MCP server - run manually")
    async def test_real_server_connection(self, echo_server_available):
        """Test connection to real MCP server.

        This test connects to the filesystem MCP server.
        Run manually with: pytest -k test_real_server -v
        """
        if not echo_server_available:
            pytest.skip("npx not available")

        transport = StdioTransport(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        )

        async with MCPClient(transport, timeout=30.0) as client:
            assert client.is_connected
            assert client.server_info is not None

            tools = await client.list_tools()
            assert len(tools) > 0

            # Find read_file tool
            tool_names = [t["name"] for t in tools]
            assert "read_file" in tool_names or "read-file" in tool_names


# =============================================================================
# Protocol Message Formatting Tests
# =============================================================================

class TestProtocolFormatting:
    """Tests for JSON-RPC protocol formatting."""

    def test_request_id_types(self):
        """Test various ID types in requests."""
        # String ID
        r1 = MCPRequest(method="test", id="string-id")
        assert r1.to_dict()["id"] == "string-id"

        # Integer ID
        r2 = MCPRequest(method="test", id=42)
        assert r2.to_dict()["id"] == 42

        # Null ID (should be included)
        r3 = MCPRequest(method="test", id=None)
        d = r3.to_dict()
        assert "id" in d
        assert d["id"] is None

    def test_response_with_null_result(self):
        """Test response with explicit null result."""
        data = {"jsonrpc": "2.0", "id": "1", "result": None}
        response = MCPResponse.from_dict(data)

        assert response.result is None
        assert not response.is_error()

    def test_nested_params(self):
        """Test deeply nested parameters."""
        request = MCPRequest(
            method="complex/call",
            params={
                "outer": {
                    "inner": {
                        "deep": ["a", "b", {"key": "value"}]
                    }
                }
            },
            id="nested",
        )
        d = request.to_dict()

        assert d["params"]["outer"]["inner"]["deep"][2]["key"] == "value"

    def test_special_characters_in_strings(self):
        """Test special characters are properly escaped."""
        request = MCPRequest(
            method="test",
            params={"path": "/path/with spaces/and\ttabs\nand\nnewlines"},
            id="special",
        )
        json_str = request.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "\t" in parsed["params"]["path"]
        assert "\n" in parsed["params"]["path"]

    def test_unicode_in_messages(self):
        """Test Unicode handling."""
        request = MCPRequest(
            method="test",
            params={"emoji": "👍", "chinese": "中文", "arabic": "العربية"},
            id="unicode",
        )
        json_str = request.to_json()
        parsed = json.loads(json_str)

        assert parsed["params"]["emoji"] == "👍"
        assert parsed["params"]["chinese"] == "中文"


# =============================================================================
# Timeout and Error Handling Tests
# =============================================================================

class TestTimeoutHandling:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_transport_receive_timeout(self):
        """Test receive timeout."""
        transport = MockTransport()
        transport._connected = True

        with pytest.raises(MCPTimeoutError) as exc_info:
            await transport.receive(timeout=0.1)

        assert exc_info.value.timeout == 0.1

    @pytest.mark.asyncio
    async def test_client_request_timeout(self):
        """Test request timeout in client."""
        transport = MockTransport()
        transport._connected = True

        client = MCPClient(transport, timeout=0.1)
        client._initialized = True

        # Start receive loop
        client._receive_task = asyncio.create_task(client._receive_loop())

        try:
            with pytest.raises(MCPTimeoutError):
                await client.list_tools()
        finally:
            client._receive_task.cancel()
            try:
                await client._receive_task
            except asyncio.CancelledError:
                pass


# =============================================================================
# Edge Cases and Regression Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and potential regressions."""

    def test_empty_params_omitted(self):
        """Test that empty params are omitted from serialization."""
        request = MCPRequest(method="test", params={}, id="1")
        d = request.to_dict()

        # Empty params should be omitted
        assert "params" not in d

    def test_response_missing_fields(self):
        """Test parsing response with missing optional fields."""
        data = {"id": "1"}  # Missing jsonrpc
        response = MCPResponse.from_dict(data)

        assert response.id == "1"
        assert response.jsonrpc == JSONRPC_VERSION  # Default

    def test_error_response_minimal(self):
        """Test error response with minimal fields."""
        data = {
            "id": "1",
            "error": {"message": "Error"},
        }
        response = MCPResponse.from_dict(data)

        assert response.error is not None
        assert response.error.message == "Error"
        assert response.error.code is None

    def test_concurrent_requests_different_ids(self):
        """Test that concurrent requests get unique IDs."""
        requests = [MCPRequest(method="test") for _ in range(100)]
        ids = [r.id for r in requests]

        # All IDs should be unique
        assert len(set(ids)) == len(ids)

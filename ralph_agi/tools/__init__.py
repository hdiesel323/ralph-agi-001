"""Tool integration module for RALPH-AGI.

This module provides dynamic tool discovery and execution using MCP
(Model Context Protocol) for 99% token reduction compared to static loading.

Three-step pattern: Discover -> Inspect -> Execute
"""

from ralph_agi.tools.mcp import (
    MCPClient,
    MCPError,
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    StdioTransport,
)

__all__ = [
    # MCP Client
    "MCPClient",
    "MCPError",
    "MCPMessage",
    "MCPNotification",
    "MCPRequest",
    "MCPResponse",
    "StdioTransport",
]

"""Tool integration module for RALPH-AGI.

This module provides dynamic tool discovery and execution using MCP
(Model Context Protocol) for 99% token reduction compared to static loading.

Three-step pattern: Discover -> Inspect -> Execute
"""

from ralph_agi.tools.cache import CacheEntry, TTLCache
from ralph_agi.tools.mcp import (
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPMessage,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    MCPTimeoutError,
    StdioTransport,
    SyncMCPClient,
)
from ralph_agi.tools.registry import (
    ServerConfig,
    ServerState,
    ServerStatus,
    ToolInfo,
    ToolRegistry,
)
from ralph_agi.tools.schema import (
    Parameter,
    SchemaParseError,
    ToolNotFoundError,
    ToolSchema,
)
from ralph_agi.tools.executor import (
    ToolError,
    ToolErrorCode,
    ToolExecutionError,
    ToolExecutor,
    ToolResult,
)
from ralph_agi.tools.filesystem import (
    BinaryFileError,
    FileInfo,
    FileSystemError,
    FileSystemTools,
    FileTooLargeError,
    PathSecurityError,
)
from ralph_agi.tools.shell import (
    CommandNotAllowedError,
    CommandResult,
    CommandTimeoutError,
    ShellError,
    ShellTools,
)
from ralph_agi.tools.git import (
    GitCommandError,
    GitCommit,
    GitError,
    GitStatus,
    GitTools,
    NotARepositoryError,
)

__all__ = [
    # MCP Client
    "MCPClient",
    "MCPConnectionError",
    "MCPError",
    "MCPMessage",
    "MCPNotification",
    "MCPRequest",
    "MCPResponse",
    "MCPTimeoutError",
    "StdioTransport",
    "SyncMCPClient",
    # Cache
    "CacheEntry",
    "TTLCache",
    # Registry
    "ServerConfig",
    "ServerState",
    "ServerStatus",
    "ToolInfo",
    "ToolRegistry",
    # Schema
    "Parameter",
    "SchemaParseError",
    "ToolNotFoundError",
    "ToolSchema",
    # Executor
    "ToolError",
    "ToolErrorCode",
    "ToolExecutionError",
    "ToolExecutor",
    "ToolResult",
    # File System (Sprint 6)
    "BinaryFileError",
    "FileInfo",
    "FileSystemError",
    "FileSystemTools",
    "FileTooLargeError",
    "PathSecurityError",
    # Shell (Sprint 6)
    "CommandNotAllowedError",
    "CommandResult",
    "CommandTimeoutError",
    "ShellError",
    "ShellTools",
    # Git (Sprint 6)
    "GitCommandError",
    "GitCommit",
    "GitError",
    "GitStatus",
    "GitTools",
    "NotARepositoryError",
]

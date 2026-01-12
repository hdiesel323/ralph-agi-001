"""Configuration management for RALPH-AGI.

This module provides YAML-based configuration loading with sensible defaults.
Configuration can be loaded from a file or created programmatically.

Key Design Principles (from PRD):
- YAML format for human readability
- Sensible defaults if config missing
- Validation of required fields
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


@dataclass
class RalphConfig:
    """Configuration for RALPH-AGI system.

    Attributes:
        max_iterations: Maximum loop iterations before forced exit. Default: 100
        completion_promise: String to detect for task completion.
            Default: "<promise>COMPLETE</promise>"
        checkpoint_interval: Iterations between checkpoints. Default: 1
        max_retries: Maximum retry attempts per iteration. Default: 3
        retry_delays: List of delays (seconds) for exponential backoff.
            Default: [1, 2, 4]
        log_file: Optional path to log file. Default: None
        checkpoint_path: Optional path for saving checkpoints. Default: None
        memory_enabled: Whether to enable persistent memory. Default: True
        memory_store_path: Path to the Memvid .mv2 file. Default: "ralph_memory.mv2"
        memory_embedding_model: Embedding model for semantic search.
            Default: "all-MiniLM-L6-v2"
        hooks_enabled: Whether to enable lifecycle hooks. Default: True
        hooks_on_iteration_start: Hook: load context at iteration start. Default: True
        hooks_on_iteration_end: Hook: store results at iteration end. Default: True
        hooks_on_error: Hook: capture errors with context. Default: True
        hooks_on_completion: Hook: store completion summary. Default: True
        hooks_context_frames: Number of context frames to load. Default: 10
    """

    max_iterations: int = 100
    completion_promise: str = "<promise>COMPLETE</promise>"
    checkpoint_interval: int = 1
    max_retries: int = 3
    retry_delays: list[int] = field(default_factory=lambda: [1, 2, 4])
    log_file: Optional[str] = None
    checkpoint_path: Optional[str] = None
    memory_enabled: bool = True
    memory_store_path: str = "ralph_memory.mv2"
    memory_embedding_model: str = "all-MiniLM-L6-v2"
    hooks_enabled: bool = True
    hooks_on_iteration_start: bool = True
    hooks_on_iteration_end: bool = True
    hooks_on_error: bool = True
    hooks_on_completion: bool = True
    hooks_context_frames: int = 10

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigValidationError: If validation fails.
        """
        if self.max_iterations < 0:
            raise ConfigValidationError("max_iterations must be non-negative")

        if self.checkpoint_interval < 1:
            raise ConfigValidationError("checkpoint_interval must be at least 1")

        if self.max_retries < 1:
            raise ConfigValidationError("max_retries must be at least 1")

        if not self.retry_delays:
            raise ConfigValidationError("retry_delays must not be empty")

        if not self.completion_promise:
            raise ConfigValidationError("completion_promise must not be empty")


def load_config(config_path: Optional[str | Path] = None) -> RalphConfig:
    """Load configuration from YAML file.

    If no path is provided, looks for 'config.yaml' in current directory.
    If file doesn't exist, returns default configuration.

    Args:
        config_path: Path to YAML config file. Default: None (uses 'config.yaml')

    Returns:
        RalphConfig instance with loaded or default values.

    Raises:
        ConfigValidationError: If config values are invalid.
        yaml.YAMLError: If YAML parsing fails.
    """
    if config_path is None:
        config_path = Path("config.yaml")
    else:
        config_path = Path(config_path)

    # Return defaults if file doesn't exist
    if not config_path.exists():
        return RalphConfig()

    # Load and parse YAML
    with open(config_path) as f:
        data = yaml.safe_load(f)

    # Handle empty file
    if data is None:
        return RalphConfig()

    # Extract config values with defaults
    # Handle nested memory config
    memory_config = data.get("memory", {})
    hooks_config = data.get("hooks", {})

    return RalphConfig(
        max_iterations=data.get("max_iterations", 100),
        completion_promise=data.get("completion_promise", "<promise>COMPLETE</promise>"),
        checkpoint_interval=data.get("checkpoint_interval", 1),
        max_retries=data.get("max_retries", 3),
        retry_delays=data.get("retry_delays", [1, 2, 4]),
        log_file=data.get("log_file"),
        checkpoint_path=data.get("checkpoint_path"),
        memory_enabled=memory_config.get("enabled", True),
        memory_store_path=memory_config.get("store_path", "ralph_memory.mv2"),
        memory_embedding_model=memory_config.get("embedding_model", "all-MiniLM-L6-v2"),
        hooks_enabled=hooks_config.get("enabled", True),
        hooks_on_iteration_start=hooks_config.get("on_iteration_start", True),
        hooks_on_iteration_end=hooks_config.get("on_iteration_end", True),
        hooks_on_error=hooks_config.get("on_error", True),
        hooks_on_completion=hooks_config.get("on_completion", True),
        hooks_context_frames=hooks_config.get("context_frames", 10),
    )


def save_config(config: RalphConfig, config_path: str | Path = "config.yaml") -> None:
    """Save configuration to YAML file.

    Args:
        config: RalphConfig instance to save.
        config_path: Path to save config file. Default: 'config.yaml'
    """
    config_path = Path(config_path)

    data = {
        "max_iterations": config.max_iterations,
        "completion_promise": config.completion_promise,
        "checkpoint_interval": config.checkpoint_interval,
        "max_retries": config.max_retries,
        "retry_delays": config.retry_delays,
        "memory": {
            "enabled": config.memory_enabled,
            "store_path": config.memory_store_path,
            "embedding_model": config.memory_embedding_model,
        },
        "hooks": {
            "enabled": config.hooks_enabled,
            "on_iteration_start": config.hooks_on_iteration_start,
            "on_iteration_end": config.hooks_on_iteration_end,
            "on_error": config.hooks_on_error,
            "on_completion": config.hooks_on_completion,
            "context_frames": config.hooks_context_frames,
        },
    }

    # Only include optional paths if set
    if config.log_file:
        data["log_file"] = config.log_file
    if config.checkpoint_path:
        data["checkpoint_path"] = config.checkpoint_path

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

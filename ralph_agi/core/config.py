"""Configuration management for RALPH-AGI.

This module provides YAML-based configuration loading with sensible defaults.
Configuration can be loaded from a file or created programmatically.

Key Design Principles (from PRD):
- YAML format for human readability
- Sensible defaults if config missing
- Validation of required fields
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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
    """

    max_iterations: int = 100
    completion_promise: str = "<promise>COMPLETE</promise>"
    checkpoint_interval: int = 1
    max_retries: int = 3
    retry_delays: list[int] = field(default_factory=lambda: [1, 2, 4])
    log_file: Optional[str] = None
    checkpoint_path: Optional[str] = None

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
    return RalphConfig(
        max_iterations=data.get("max_iterations", 100),
        completion_promise=data.get("completion_promise", "<promise>COMPLETE</promise>"),
        checkpoint_interval=data.get("checkpoint_interval", 1),
        max_retries=data.get("max_retries", 3),
        retry_delays=data.get("retry_delays", [1, 2, 4]),
        log_file=data.get("log_file"),
        checkpoint_path=data.get("checkpoint_path"),
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
    }

    # Only include optional paths if set
    if config.log_file:
        data["log_file"] = config.log_file
    if config.checkpoint_path:
        data["checkpoint_path"] = config.checkpoint_path

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

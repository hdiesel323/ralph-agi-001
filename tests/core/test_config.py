"""Tests for the configuration management module.

Tests cover:
- RalphConfig initialization with defaults
- RalphConfig validation
- YAML config loading
- Missing config file handling
- Config saving
- Integration with RalphLoop
"""

import pytest

from ralph_agi.core.config import (
    ConfigValidationError,
    RalphConfig,
    load_config,
    save_config,
)
from ralph_agi.core.loop import RalphLoop


class TestRalphConfigDefaults:
    """Tests for RalphConfig default values."""

    def test_default_max_iterations(self):
        """Test default max_iterations is 100."""
        config = RalphConfig()
        assert config.max_iterations == 100

    def test_default_completion_promise(self):
        """Test default completion_promise."""
        config = RalphConfig()
        assert config.completion_promise == "<promise>COMPLETE</promise>"

    def test_default_checkpoint_interval(self):
        """Test default checkpoint_interval is 1."""
        config = RalphConfig()
        assert config.checkpoint_interval == 1

    def test_default_max_retries(self):
        """Test default max_retries is 3."""
        config = RalphConfig()
        assert config.max_retries == 3

    def test_default_retry_delays(self):
        """Test default retry_delays."""
        config = RalphConfig()
        assert config.retry_delays == [1, 2, 4]

    def test_default_log_file_is_none(self):
        """Test default log_file is None."""
        config = RalphConfig()
        assert config.log_file is None


class TestRalphConfigCustomValues:
    """Tests for RalphConfig with custom values."""

    def test_custom_max_iterations(self):
        """Test custom max_iterations."""
        config = RalphConfig(max_iterations=50)
        assert config.max_iterations == 50

    def test_custom_completion_promise(self):
        """Test custom completion_promise."""
        config = RalphConfig(completion_promise="DONE")
        assert config.completion_promise == "DONE"

    def test_custom_checkpoint_interval(self):
        """Test custom checkpoint_interval."""
        config = RalphConfig(checkpoint_interval=5)
        assert config.checkpoint_interval == 5

    def test_custom_retry_config(self):
        """Test custom retry configuration."""
        config = RalphConfig(max_retries=5, retry_delays=[2, 4, 8, 16])
        assert config.max_retries == 5
        assert config.retry_delays == [2, 4, 8, 16]

    def test_custom_log_file(self):
        """Test custom log_file."""
        config = RalphConfig(log_file="test.log")
        assert config.log_file == "test.log"


class TestRalphConfigValidation:
    """Tests for RalphConfig validation."""

    def test_negative_max_iterations_raises(self):
        """Test that negative max_iterations raises error."""
        with pytest.raises(ConfigValidationError, match="max_iterations"):
            RalphConfig(max_iterations=-1)

    def test_zero_max_iterations_allowed(self):
        """Test that zero max_iterations is allowed."""
        config = RalphConfig(max_iterations=0)
        assert config.max_iterations == 0

    def test_zero_checkpoint_interval_raises(self):
        """Test that zero checkpoint_interval raises error."""
        with pytest.raises(ConfigValidationError, match="checkpoint_interval"):
            RalphConfig(checkpoint_interval=0)

    def test_zero_max_retries_raises(self):
        """Test that zero max_retries raises error."""
        with pytest.raises(ConfigValidationError, match="max_retries"):
            RalphConfig(max_retries=0)

    def test_empty_retry_delays_raises(self):
        """Test that empty retry_delays raises error."""
        with pytest.raises(ConfigValidationError, match="retry_delays"):
            RalphConfig(retry_delays=[])

    def test_empty_completion_promise_raises(self):
        """Test that empty completion_promise raises error."""
        with pytest.raises(ConfigValidationError, match="completion_promise"):
            RalphConfig(completion_promise="")


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_missing_file_returns_defaults(self, tmp_path):
        """Test that missing config file returns defaults."""
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.max_iterations == 100
        assert config.completion_promise == "<promise>COMPLETE</promise>"

    def test_load_empty_file_returns_defaults(self, tmp_path):
        """Test that empty config file returns defaults."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = load_config(config_file)
        assert config.max_iterations == 100

    def test_load_partial_config(self, tmp_path):
        """Test loading config with only some values set."""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text("max_iterations: 50\n")

        config = load_config(config_file)
        assert config.max_iterations == 50
        assert config.completion_promise == "<promise>COMPLETE</promise>"

    def test_load_full_config(self, tmp_path):
        """Test loading config with all values set."""
        config_file = tmp_path / "full.yaml"
        config_file.write_text("""
max_iterations: 200
completion_promise: "FINISHED"
checkpoint_interval: 10
max_retries: 5
retry_delays: [1, 3, 9]
log_file: "output.log"
""")

        config = load_config(config_file)
        assert config.max_iterations == 200
        assert config.completion_promise == "FINISHED"
        assert config.checkpoint_interval == 10
        assert config.max_retries == 5
        assert config.retry_delays == [1, 3, 9]
        assert config.log_file == "output.log"

    def test_load_default_path(self, tmp_path, monkeypatch):
        """Test loading from default config.yaml path."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 42\n")

        config = load_config()
        assert config.max_iterations == 42


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test that saved config can be loaded back."""
        config_file = tmp_path / "test.yaml"
        original = RalphConfig(
            max_iterations=75,
            completion_promise="DONE",
            checkpoint_interval=3,
        )

        save_config(original, config_file)
        loaded = load_config(config_file)

        assert loaded.max_iterations == original.max_iterations
        assert loaded.completion_promise == original.completion_promise
        assert loaded.checkpoint_interval == original.checkpoint_interval

    def test_save_creates_file(self, tmp_path):
        """Test that save_config creates the file."""
        config_file = tmp_path / "new.yaml"
        config = RalphConfig()

        save_config(config, config_file)

        assert config_file.exists()

    def test_save_excludes_none_log_file(self, tmp_path):
        """Test that None log_file is not saved."""
        config_file = tmp_path / "test.yaml"
        config = RalphConfig(log_file=None)

        save_config(config, config_file)
        content = config_file.read_text()

        assert "log_file" not in content


class TestRalphLoopFromConfig:
    """Tests for RalphLoop.from_config integration."""

    def test_from_config_uses_values(self):
        """Test that from_config uses config values."""
        config = RalphConfig(
            max_iterations=50,
            completion_promise="DONE",
            max_retries=5,
            retry_delays=[2, 4],
        )

        loop = RalphLoop.from_config(config)

        assert loop.max_iterations == 50
        assert loop._completion_signal == "DONE"
        assert loop.max_retries == 5
        assert loop.retry_delays == [2, 4]

    def test_from_config_with_log_file(self, tmp_path):
        """Test from_config with log_file set."""
        log_file = tmp_path / "test.log"
        config = RalphConfig(log_file=str(log_file))

        loop = RalphLoop.from_config(config)
        loop.run()
        loop.close()

        assert log_file.exists()

    def test_custom_completion_promise_detected(self):
        """Test that custom completion promise is detected."""
        config = RalphConfig(
            max_iterations=10,
            completion_promise="ALL_DONE",
        )

        loop = RalphLoop.from_config(config)

        # Test detection
        assert loop._check_completion("Task finished ALL_DONE here") is True
        assert loop._check_completion("<promise>COMPLETE</promise>") is False

    def test_load_config_and_run(self, tmp_path):
        """Test full workflow: load config and run loop."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
max_iterations: 3
completion_promise: "FINISHED"
""")

        config = load_config(config_file)
        loop = RalphLoop.from_config(config)
        result = loop.run()

        assert result is False  # Reached max iterations
        assert loop.iteration == 3

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

    def test_default_memory_enabled(self):
        """Test default memory_enabled is True."""
        config = RalphConfig()
        assert config.memory_enabled is True

    def test_default_memory_store_path(self):
        """Test default memory_store_path."""
        config = RalphConfig()
        assert config.memory_store_path == "ralph_memory.mv2"

    def test_default_memory_embedding_model(self):
        """Test default memory_embedding_model."""
        config = RalphConfig()
        assert config.memory_embedding_model == "all-MiniLM-L6-v2"

    def test_default_hooks_enabled(self):
        """Test default hooks_enabled is True."""
        config = RalphConfig()
        assert config.hooks_enabled is True

    def test_default_hooks_on_iteration_start(self):
        """Test default hooks_on_iteration_start is True."""
        config = RalphConfig()
        assert config.hooks_on_iteration_start is True

    def test_default_hooks_on_iteration_end(self):
        """Test default hooks_on_iteration_end is True."""
        config = RalphConfig()
        assert config.hooks_on_iteration_end is True

    def test_default_hooks_on_error(self):
        """Test default hooks_on_error is True."""
        config = RalphConfig()
        assert config.hooks_on_error is True

    def test_default_hooks_on_completion(self):
        """Test default hooks_on_completion is True."""
        config = RalphConfig()
        assert config.hooks_on_completion is True

    def test_default_hooks_context_frames(self):
        """Test default hooks_context_frames is 10."""
        config = RalphConfig()
        assert config.hooks_context_frames == 10


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

    def test_custom_memory_config(self):
        """Test custom memory configuration."""
        config = RalphConfig(
            memory_enabled=False,
            memory_store_path="/custom/path.mv2",
        )
        assert config.memory_enabled is False
        assert config.memory_store_path == "/custom/path.mv2"

    def test_custom_embedding_model(self):
        """Test custom embedding model configuration."""
        config = RalphConfig(
            memory_embedding_model="all-mpnet-base-v2",
        )
        assert config.memory_embedding_model == "all-mpnet-base-v2"

    def test_custom_hooks_enabled(self):
        """Test custom hooks_enabled."""
        config = RalphConfig(hooks_enabled=False)
        assert config.hooks_enabled is False

    def test_custom_hooks_config(self):
        """Test custom hooks configuration."""
        config = RalphConfig(
            hooks_on_iteration_start=False,
            hooks_on_error=False,
            hooks_context_frames=20,
        )
        assert config.hooks_on_iteration_start is False
        assert config.hooks_on_error is False
        assert config.hooks_context_frames == 20


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

    def test_load_memory_config(self, tmp_path):
        """Test loading memory config from YAML."""
        config_file = tmp_path / "memory.yaml"
        config_file.write_text("""
memory:
  enabled: false
  store_path: "/custom/memory.mv2"
""")

        config = load_config(config_file)
        assert config.memory_enabled is False
        assert config.memory_store_path == "/custom/memory.mv2"

    def test_load_embedding_model_config(self, tmp_path):
        """Test loading embedding_model from YAML."""
        config_file = tmp_path / "embedding.yaml"
        config_file.write_text("""
memory:
  embedding_model: "all-mpnet-base-v2"
""")

        config = load_config(config_file)
        assert config.memory_embedding_model == "all-mpnet-base-v2"

    def test_load_memory_defaults_when_missing(self, tmp_path):
        """Test that memory defaults are used when not in config."""
        config_file = tmp_path / "no_memory.yaml"
        config_file.write_text("max_iterations: 10\n")

        config = load_config(config_file)
        assert config.memory_enabled is True
        assert config.memory_store_path == "ralph_memory.mv2"

    def test_load_hooks_config(self, tmp_path):
        """Test loading hooks config from YAML."""
        config_file = tmp_path / "hooks.yaml"
        config_file.write_text("""
hooks:
  enabled: false
  on_iteration_start: false
  on_error: false
  context_frames: 25
""")

        config = load_config(config_file)
        assert config.hooks_enabled is False
        assert config.hooks_on_iteration_start is False
        assert config.hooks_on_error is False
        assert config.hooks_context_frames == 25

    def test_load_hooks_defaults_when_missing(self, tmp_path):
        """Test that hooks defaults are used when not in config."""
        config_file = tmp_path / "no_hooks.yaml"
        config_file.write_text("max_iterations: 10\n")

        config = load_config(config_file)
        assert config.hooks_enabled is True
        assert config.hooks_on_iteration_start is True
        assert config.hooks_context_frames == 10


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

    def test_save_and_load_memory_config_roundtrip(self, tmp_path):
        """Test that memory config roundtrips correctly."""
        config_file = tmp_path / "memory_test.yaml"
        original = RalphConfig(
            memory_enabled=False,
            memory_store_path="/custom/path.mv2",
        )

        save_config(original, config_file)
        loaded = load_config(config_file)

        assert loaded.memory_enabled == original.memory_enabled
        assert loaded.memory_store_path == original.memory_store_path

    def test_save_and_load_embedding_model_roundtrip(self, tmp_path):
        """Test that embedding_model config roundtrips correctly."""
        config_file = tmp_path / "embedding_test.yaml"
        original = RalphConfig(
            memory_embedding_model="all-mpnet-base-v2",
        )

        save_config(original, config_file)
        loaded = load_config(config_file)

        assert loaded.memory_embedding_model == original.memory_embedding_model

    def test_save_and_load_hooks_config_roundtrip(self, tmp_path):
        """Test that hooks config roundtrips correctly."""
        config_file = tmp_path / "hooks_test.yaml"
        original = RalphConfig(
            hooks_enabled=False,
            hooks_on_iteration_start=False,
            hooks_on_error=False,
            hooks_context_frames=25,
        )

        save_config(original, config_file)
        loaded = load_config(config_file)

        assert loaded.hooks_enabled == original.hooks_enabled
        assert loaded.hooks_on_iteration_start == original.hooks_on_iteration_start
        assert loaded.hooks_on_error == original.hooks_on_error
        assert loaded.hooks_context_frames == original.hooks_context_frames

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


class TestLLMConfig:
    """Tests for LLM configuration options."""

    def test_default_builder_model(self):
        """Test default builder model."""
        config = RalphConfig()
        assert config.llm_builder_model == "claude-sonnet-4-20250514"

    def test_default_builder_provider(self):
        """Test default builder provider."""
        config = RalphConfig()
        assert config.llm_builder_provider == "anthropic"

    def test_default_critic_model(self):
        """Test default critic model."""
        config = RalphConfig()
        assert config.llm_critic_model == "gpt-4o"

    def test_default_critic_provider(self):
        """Test default critic provider."""
        config = RalphConfig()
        assert config.llm_critic_provider == "openai"

    def test_default_critic_enabled(self):
        """Test default critic_enabled."""
        config = RalphConfig()
        assert config.llm_critic_enabled is True

    def test_default_max_tokens(self):
        """Test default max_tokens."""
        config = RalphConfig()
        assert config.llm_max_tokens == 4096

    def test_default_max_tool_iterations(self):
        """Test default max_tool_iterations."""
        config = RalphConfig()
        assert config.llm_max_tool_iterations == 10

    def test_default_temperature(self):
        """Test default temperature."""
        config = RalphConfig()
        assert config.llm_temperature == 0.0

    def test_default_rate_limit_retries(self):
        """Test default rate_limit_retries."""
        config = RalphConfig()
        assert config.llm_rate_limit_retries == 3

    def test_custom_llm_values(self):
        """Test custom LLM configuration values."""
        config = RalphConfig(
            llm_builder_model="claude-opus-4-20250514",
            llm_builder_provider="openrouter",
            llm_critic_model="o1",
            llm_critic_provider="openrouter",
            llm_critic_enabled=False,
            llm_max_tokens=8192,
            llm_max_tool_iterations=20,
            llm_temperature=0.5,
            llm_rate_limit_retries=5,
        )

        assert config.llm_builder_model == "claude-opus-4-20250514"
        assert config.llm_builder_provider == "openrouter"
        assert config.llm_critic_model == "o1"
        assert config.llm_critic_provider == "openrouter"
        assert config.llm_critic_enabled is False
        assert config.llm_max_tokens == 8192
        assert config.llm_max_tool_iterations == 20
        assert config.llm_temperature == 0.5
        assert config.llm_rate_limit_retries == 5

    def test_load_llm_config_from_yaml(self, tmp_path):
        """Test loading LLM config from YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  builder_model: claude-opus-4-20250514
  builder_provider: openrouter
  critic_model: o1
  critic_provider: openrouter
  critic_enabled: false
  max_tokens: 8192
  max_tool_iterations: 20
  temperature: 0.7
  rate_limit_retries: 5
""")

        config = load_config(config_file)

        assert config.llm_builder_model == "claude-opus-4-20250514"
        assert config.llm_builder_provider == "openrouter"
        assert config.llm_critic_model == "o1"
        assert config.llm_critic_provider == "openrouter"
        assert config.llm_critic_enabled is False
        assert config.llm_max_tokens == 8192
        assert config.llm_max_tool_iterations == 20
        assert config.llm_temperature == 0.7
        assert config.llm_rate_limit_retries == 5

    def test_load_partial_llm_config(self, tmp_path):
        """Test loading partial LLM config with defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  builder_model: claude-opus-4-20250514
  critic_enabled: false
""")

        config = load_config(config_file)

        assert config.llm_builder_model == "claude-opus-4-20250514"
        assert config.llm_builder_provider == "anthropic"  # default
        assert config.llm_critic_enabled is False
        assert config.llm_max_tokens == 4096  # default

    def test_save_and_load_llm_config_roundtrip(self, tmp_path):
        """Test save and load roundtrip for LLM config."""
        config_file = tmp_path / "config.yaml"

        original = RalphConfig(
            llm_builder_model="claude-opus-4-20250514",
            llm_builder_provider="openrouter",
            llm_critic_model="o1",
            llm_critic_provider="openai",
            llm_critic_enabled=False,
            llm_max_tokens=8192,
            llm_max_tool_iterations=15,
            llm_temperature=0.3,
            llm_rate_limit_retries=7,
        )

        save_config(original, config_file)
        loaded = load_config(config_file)

        assert loaded.llm_builder_model == original.llm_builder_model
        assert loaded.llm_builder_provider == original.llm_builder_provider
        assert loaded.llm_critic_model == original.llm_critic_model
        assert loaded.llm_critic_provider == original.llm_critic_provider
        assert loaded.llm_critic_enabled == original.llm_critic_enabled
        assert loaded.llm_max_tokens == original.llm_max_tokens
        assert loaded.llm_max_tool_iterations == original.llm_max_tool_iterations
        assert loaded.llm_temperature == original.llm_temperature
        assert loaded.llm_rate_limit_retries == original.llm_rate_limit_retries

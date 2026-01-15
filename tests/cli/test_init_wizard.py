"""Tests for ralph_agi.init_wizard module."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ralph_agi.init_wizard import (
    PROVIDERS,
    GIT_WORKFLOWS,
    WizardOptions,
    _check_api_key,
    generate_sample_prd,
    run_wizard,
)


class TestWizardOptions:
    """Tests for WizardOptions dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        options = WizardOptions()
        assert options.builder_provider == "anthropic"
        assert options.builder_model == "claude-sonnet-4-20250514"
        assert options.critic_provider == "openai"
        assert options.critic_model == "gpt-4o"
        assert options.critic_enabled is True
        assert options.git_workflow == "branch"
        assert options.git_auto_push is True
        assert options.max_iterations == 100
        assert options.memory_enabled is True

    def test_custom_values(self):
        """Test custom values can be set."""
        options = WizardOptions(
            builder_provider="openrouter",
            builder_model="anthropic/claude-sonnet-4",
            git_workflow="pr",
            max_iterations=50,
        )
        assert options.builder_provider == "openrouter"
        assert options.builder_model == "anthropic/claude-sonnet-4"
        assert options.git_workflow == "pr"
        assert options.max_iterations == 50


class TestProviders:
    """Tests for provider configurations."""

    def test_providers_have_required_keys(self):
        """Test all providers have required configuration keys."""
        for provider_id, config in PROVIDERS.items():
            assert "name" in config
            assert "env_var" in config
            assert "models" in config
            assert len(config["models"]) > 0

    def test_provider_models_are_tuples(self):
        """Test provider models are (id, description) tuples."""
        for provider_id, config in PROVIDERS.items():
            for model in config["models"]:
                assert isinstance(model, tuple)
                assert len(model) == 2
                assert isinstance(model[0], str)  # model id
                assert isinstance(model[1], str)  # description


class TestGitWorkflows:
    """Tests for git workflow configurations."""

    def test_all_workflows_defined(self):
        """Test all expected workflows are defined."""
        assert "branch" in GIT_WORKFLOWS
        assert "pr" in GIT_WORKFLOWS
        assert "direct" in GIT_WORKFLOWS

    def test_workflows_have_descriptions(self):
        """Test all workflows have descriptions."""
        for workflow, desc in GIT_WORKFLOWS.items():
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestCheckApiKey:
    """Tests for API key detection."""

    def test_api_key_present(self):
        """Test detection when API key is set."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            is_set, env_var = _check_api_key("anthropic")
            assert is_set is True
            assert env_var == "ANTHROPIC_API_KEY"

    def test_api_key_missing(self):
        """Test detection when API key is not set."""
        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            is_set, env_var = _check_api_key("anthropic")
            assert is_set is False
            assert env_var == "ANTHROPIC_API_KEY"

    def test_openai_api_key(self):
        """Test OpenAI API key detection."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            is_set, env_var = _check_api_key("openai")
            assert is_set is True
            assert env_var == "OPENAI_API_KEY"

    def test_openrouter_api_key(self):
        """Test OpenRouter API key detection."""
        is_set, env_var = _check_api_key("openrouter")
        assert env_var == "OPENROUTER_API_KEY"


class TestRunWizardQuickMode:
    """Tests for run_wizard in quick mode."""

    def test_quick_mode_creates_config(self):
        """Test quick mode creates config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "config.yaml"

            success, message = run_wizard(quick=True, output_path=str(output_path))

            assert success is True
            assert output_path.exists()
            assert "saved" in message.lower()

    def test_quick_mode_config_is_valid_yaml(self):
        """Test generated config is valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "config.yaml"
            run_wizard(quick=True, output_path=str(output_path))

            with open(output_path) as f:
                config = yaml.safe_load(f)

            assert config is not None
            assert "max_iterations" in config
            assert "llm" in config
            assert "git" in config

    def test_quick_mode_uses_defaults(self):
        """Test quick mode uses default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "config.yaml"
            run_wizard(quick=True, output_path=str(output_path))

            with open(output_path) as f:
                config = yaml.safe_load(f)

            assert config["max_iterations"] == 100
            assert config["llm"]["builder_provider"] == "anthropic"
            assert config["git"]["workflow"] == "branch"

    def test_existing_config_not_overwritten_by_default(self):
        """Test existing config is preserved when user declines overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "config.yaml"

            # Create existing config
            output_path.write_text("existing: true")

            # Mock user input to decline overwrite
            with patch("builtins.input", return_value="n"):
                success, message = run_wizard(quick=True, output_path=str(output_path))

            assert success is False
            assert "cancelled" in message.lower() or "preserved" in message.lower()

            # Verify original content preserved
            assert output_path.read_text() == "existing: true"


class TestGenerateSamplePrd:
    """Tests for sample PRD generation."""

    def test_creates_prd_file(self):
        """Test sample PRD file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "PRD.json"

            success, message = generate_sample_prd(str(output_path))

            assert success is True
            assert output_path.exists()

    def test_prd_is_valid_json(self):
        """Test generated PRD is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "PRD.json"
            generate_sample_prd(str(output_path))

            with open(output_path) as f:
                prd = json.load(f)

            assert prd is not None
            assert "project" in prd
            assert "features" in prd

    def test_prd_has_required_structure(self):
        """Test PRD has required structure for ralph-agi."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "PRD.json"
            generate_sample_prd(str(output_path))

            with open(output_path) as f:
                prd = json.load(f)

            # Check project section
            assert "name" in prd["project"]
            assert "description" in prd["project"]

            # Check features section
            assert len(prd["features"]) > 0
            feature = prd["features"][0]
            assert "id" in feature
            assert "name" in feature
            assert "tasks" in feature

            # Check tasks
            assert len(feature["tasks"]) > 0
            task = feature["tasks"][0]
            assert "id" in task
            assert "description" in task
            assert "status" in task

    def test_does_not_overwrite_existing(self):
        """Test existing PRD is not overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "PRD.json"

            # Create existing PRD
            output_path.write_text('{"existing": true}')

            success, message = generate_sample_prd(str(output_path))

            assert success is False
            assert "exists" in message.lower()

            # Verify original content preserved
            assert output_path.read_text() == '{"existing": true}'


class TestCliIntegration:
    """Tests for CLI integration with init command."""

    def test_init_command_available(self):
        """Test init command is registered in CLI."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["init"])
        assert args.command == "init"

    def test_init_quick_flag(self):
        """Test --quick flag is parsed."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["init", "--quick"])
        assert args.quick is True

    def test_init_output_flag(self):
        """Test --output flag is parsed."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["init", "--output", "custom.yaml"])
        assert args.output == "custom.yaml"

    def test_init_sample_prd_flag(self):
        """Test --sample-prd flag is parsed."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["init", "--sample-prd"])
        assert args.sample_prd is True

    def test_init_all_flags_together(self):
        """Test all flags can be used together."""
        from ralph_agi.cli import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "init",
            "--quick",
            "--output", "my-config.yaml",
            "--sample-prd",
        ])
        assert args.quick is True
        assert args.output == "my-config.yaml"
        assert args.sample_prd is True


class TestRunInit:
    """Tests for run_init CLI handler."""

    def test_run_init_quick_mode(self):
        """Test run_init in quick mode."""
        from ralph_agi.cli import EXIT_SUCCESS, main

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "config.yaml"

            exit_code = main(["init", "--quick", "--output", str(output_path)])

            assert exit_code == EXIT_SUCCESS
            assert output_path.exists()

    def test_run_init_with_sample_prd(self):
        """Test run_init generates sample PRD when requested."""
        from ralph_agi.cli import EXIT_SUCCESS, main

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory so PRD is created there
            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                output_path = Path(tmpdir) / "config.yaml"

                exit_code = main([
                    "init",
                    "--quick",
                    "--output", str(output_path),
                    "--sample-prd",
                ])

                assert exit_code == EXIT_SUCCESS
                assert output_path.exists()
                assert (Path(tmpdir) / "PRD.json").exists()
            finally:
                os.chdir(original_cwd)

"""Tests for ralph_agi.cli module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ralph_agi.cli import (
    EXIT_ERROR,
    EXIT_MAX_ITERATIONS,
    EXIT_SUCCESS,
    create_parser,
    main,
    run_loop,
)


class TestCreateParser:
    def test_help_flag_shows_usage(self, capsys):
        """Test --help flag shows usage information."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower()
    """Tests for argument parser creation."""

    def test_parser_created(self):
        """Test parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "ralph-agi"

    def test_parser_has_run_command(self):
        """Test parser has run subcommand."""
        parser = create_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"

    def test_parser_version_flag(self):
        """Test --version flag is available."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0

    def test_run_max_iterations(self):
        """Test --max-iterations flag."""
        parser = create_parser()
        args = parser.parse_args(["run", "--max-iterations", "50"])
        assert args.max_iterations == 50

    def test_run_config_flag(self):
        """Test --config flag."""
        parser = create_parser()
        args = parser.parse_args(["run", "--config", "custom.yaml"])
        assert args.config == "custom.yaml"

    def test_run_config_short_flag(self):
        """Test -c short flag for config."""
        parser = create_parser()
        args = parser.parse_args(["run", "-c", "custom.yaml"])
        assert args.config == "custom.yaml"

    def test_run_verbose_flag(self):
        """Test --verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["run", "--verbose"])
        assert args.verbose is True

    def test_run_verbose_short_flag(self):
        """Test -v short flag for verbose."""
        parser = create_parser()
        args = parser.parse_args(["run", "-v"])
        assert args.verbose is True

    def test_run_quiet_flag(self):
        """Test --quiet flag."""
        parser = create_parser()
        args = parser.parse_args(["run", "--quiet"])
        assert args.quiet is True

    def test_run_quiet_short_flag(self):
        """Test -q short flag for quiet."""
        parser = create_parser()
        args = parser.parse_args(["run", "-q"])
        assert args.quiet is True

    def test_run_default_config(self):
        """Test default config path."""
        parser = create_parser()
        args = parser.parse_args(["run"])
        assert args.config == "config.yaml"


class TestMainFunction:
    """Tests for main() entry point."""

    def test_main_no_command_shows_help(self, capsys):
        """Test main with no command shows help."""
        result = main([])
        assert result == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "ralph-agi" in captured.out or "usage" in captured.out.lower()

    def test_main_help_flag(self):
        """Test main with --help flag."""
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0

    @patch("ralph_agi.cli.run_loop")
    def test_main_run_command(self, mock_run_loop):
        """Test main dispatches to run_loop."""
        mock_run_loop.return_value = EXIT_SUCCESS
        result = main(["run"])
        mock_run_loop.assert_called_once()
        assert result == EXIT_SUCCESS


class TestRunLoop:
    """Tests for run_loop() function."""

    def test_run_loop_config_not_found(self, tmp_path):
        """Test run_loop with non-existent config."""
        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(tmp_path / "missing.yaml")])
        # Config file doesn't exist, but load_config returns defaults
        # This should not fail since load_config returns defaults
        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.return_value = True
            mock_loop.iteration = 0
            mock_loop.session_id = "test-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            # Should succeed since defaults are used
            assert result == EXIT_SUCCESS

    def test_run_loop_success(self, tmp_path):
        """Test run_loop with successful completion."""
        # Create a minimal config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 5\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file)])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.return_value = True  # Completed successfully
            mock_loop.iteration = 2
            mock_loop.session_id = "test-session-123"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            assert result == EXIT_SUCCESS
            mock_loop.close.assert_called_once()

    def test_run_loop_max_iterations(self, tmp_path):
        """Test run_loop returns EXIT_MAX_ITERATIONS when max reached."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 5\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file)])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.return_value = False  # Max iterations reached
            mock_loop.iteration = 5
            mock_loop.session_id = "test-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            assert result == EXIT_MAX_ITERATIONS
            mock_loop.close.assert_called_once()

    def test_run_loop_with_max_iterations_override(self, tmp_path):
        """Test --max-iterations overrides config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 100\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(
            ["run", "--config", str(config_file), "--max-iterations", "10"]
        )

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.return_value = True
            mock_loop.iteration = 5
            mock_loop.session_id = "test-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            # Check that from_config was called with overridden value
            call_args = mock_loop_class.from_config.call_args
            config = call_args[0][0]
            assert config.max_iterations == 10

    def test_run_loop_verbose_mode(self, tmp_path):
        """Test run_loop with verbose flag."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 2\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file), "-v"])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.return_value = True
            mock_loop.iteration = 1
            mock_loop.session_id = "verbose-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            assert result == EXIT_SUCCESS

    def test_run_loop_quiet_mode(self, tmp_path):
        """Test run_loop with quiet flag."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 2\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file), "-q"])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.return_value = True
            mock_loop.iteration = 1
            mock_loop.session_id = "quiet-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            assert result == EXIT_SUCCESS

    def test_run_loop_dry_run_requires_prd(self, tmp_path, capsys):
        """Test dry-run requires --prd flag."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 10\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--dry-run", "--config", str(config_file)])

        result = run_loop(args)
        assert result == EXIT_ERROR

        captured = capsys.readouterr()
        assert "--dry-run requires --prd" in captured.out

    def test_run_loop_dry_run_shows_real_task(self, tmp_path, capsys):
        """Test dry-run shows actual task from PRD."""
        import json

        # Create config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 10\nmemory:\n  enabled: false\n")

        # Create PRD with pending task
        prd_file = tmp_path / "PRD.json"
        prd_data = {
            "project": {
                "name": "Test Project",
                "description": "A test project for dry-run",
            },
            "features": [
                {
                    "id": "TEST-001",
                    "description": "A test task",
                    "passes": False,
                    "priority": 1,
                    "acceptance_criteria": ["Task should work"],
                }
            ],
        }
        prd_file.write_text(json.dumps(prd_data))

        parser = create_parser()
        args = parser.parse_args(
            ["run", "--dry-run", "--prd", str(prd_file), "--config", str(config_file)]
        )

        result = run_loop(args)
        assert result == EXIT_SUCCESS

        captured = capsys.readouterr()
        # Verify real task info is shown
        assert "DRY-RUN MODE" in captured.out
        assert "Test Project" in captured.out
        assert "TEST-001" in captured.out
        assert "A test task" in captured.out
        assert "AVAILABLE TOOLS" in captured.out
        assert "read_file" in captured.out

    def test_run_loop_dry_run_all_complete(self, tmp_path, capsys):
        """Test dry-run shows all complete when no pending tasks."""
        import json

        # Create config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 10\nmemory:\n  enabled: false\n")

        # Create PRD with completed task
        prd_file = tmp_path / "PRD.json"
        prd_data = {
            "project": {"name": "Done Project", "description": "All tasks done"},
            "features": [
                {"id": "DONE-001", "description": "Already done", "passes": True}
            ],
        }
        prd_file.write_text(json.dumps(prd_data))

        parser = create_parser()
        args = parser.parse_args(
            ["run", "--dry-run", "--prd", str(prd_file), "--config", str(config_file)]
        )

        result = run_loop(args)
        assert result == EXIT_SUCCESS

        captured = capsys.readouterr()
        assert "ALL TASKS COMPLETE" in captured.out


class TestRunLoopExceptions:
    """Tests for exception handling in run_loop."""

    def test_run_loop_loop_interrupted(self, tmp_path):
        """Test run_loop handles LoopInterrupted gracefully."""
        from ralph_agi.core.loop import LoopInterrupted

        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 10\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file)])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.side_effect = LoopInterrupted(
                "Interrupted", iteration=3, checkpoint_path="/tmp/checkpoint.json"
            )
            mock_loop.session_id = "interrupted-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            # Graceful interrupt is success
            assert result == EXIT_SUCCESS
            mock_loop.close.assert_called_once()

    def test_run_loop_max_retries_exceeded(self, tmp_path):
        """Test run_loop handles MaxRetriesExceeded."""
        from ralph_agi.core.loop import MaxRetriesExceeded

        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 10\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file)])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.side_effect = MaxRetriesExceeded(
                "Failed after retries", attempts=3, last_error=ValueError("bad")
            )
            mock_loop.session_id = "retry-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            assert result == EXIT_ERROR
            mock_loop.close.assert_called_once()

    def test_run_loop_unexpected_exception(self, tmp_path):
        """Test run_loop handles unexpected exceptions."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("max_iterations: 10\nmemory:\n  enabled: false\n")

        parser = create_parser()
        args = parser.parse_args(["run", "--config", str(config_file)])

        with patch("ralph_agi.cli.RalphLoop") as mock_loop_class:
            mock_loop = MagicMock()
            mock_loop.run.side_effect = RuntimeError("Something unexpected")
            mock_loop.session_id = "error-session"
            mock_loop_class.from_config.return_value = mock_loop

            result = run_loop(args)
            assert result == EXIT_ERROR
            mock_loop.close.assert_called_once()


class TestExitCodes:
    """Tests for exit code constants."""

    def test_exit_codes_are_distinct(self):
        """Test exit codes are different values."""
        codes = {EXIT_SUCCESS, EXIT_ERROR, EXIT_MAX_ITERATIONS}
        assert len(codes) == 3

    def test_exit_success_is_zero(self):
        """Test EXIT_SUCCESS is 0."""
        assert EXIT_SUCCESS == 0

    def test_exit_error_is_one(self):
        """Test EXIT_ERROR is 1."""
        assert EXIT_ERROR == 1

    def test_exit_max_iterations_is_two(self):
        """Test EXIT_MAX_ITERATIONS is 2."""
        assert EXIT_MAX_ITERATIONS == 2

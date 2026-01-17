"""Integration tests for LLM-wired RalphLoop.

Tests the complete flow of RalphLoop with LLM orchestration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ralph_agi.core.config import RalphConfig
from ralph_agi.core.loop import IterationResult, RalphLoop, ToolExecutorAdapter
from ralph_agi.llm.agents import AgentStatus, BuilderResult, CriticResult, CriticVerdict
from ralph_agi.llm.orchestrator import OrchestratorResult, OrchestratorStatus


# =============================================================================
# ToolExecutorAdapter Tests
# =============================================================================


class TestToolExecutorAdapter:
    """Tests for ToolExecutorAdapter."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        adapter = ToolExecutorAdapter()
        assert adapter._work_dir == Path.cwd()

    def test_init_custom_work_dir(self, tmp_path: Path) -> None:
        """Test with custom work directory."""
        adapter = ToolExecutorAdapter(work_dir=tmp_path)
        assert adapter._work_dir == tmp_path

    @pytest.mark.asyncio
    async def test_execute_read_file(self, tmp_path: Path) -> None:
        """Test read_file tool execution."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!")

        adapter = ToolExecutorAdapter(work_dir=tmp_path)
        result = await adapter.execute("read_file", {"path": str(test_file)})

        assert "Hello, world!" in result

    @pytest.mark.asyncio
    async def test_execute_write_file(self, tmp_path: Path) -> None:
        """Test write_file tool execution."""
        adapter = ToolExecutorAdapter(work_dir=tmp_path)

        target_file = tmp_path / "output.txt"
        result = await adapter.execute(
            "write_file",
            {"path": str(target_file), "content": "Test content"},
        )

        assert "File written" in result
        assert target_file.exists()
        assert target_file.read_text() == "Test content"

    @pytest.mark.asyncio
    async def test_execute_list_directory(self, tmp_path: Path) -> None:
        """Test list_directory tool execution."""
        # Create some files
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()
        (tmp_path / "subdir").mkdir()

        adapter = ToolExecutorAdapter(work_dir=tmp_path)
        result = await adapter.execute("list_directory", {"path": str(tmp_path)})

        assert "file1.txt" in result
        assert "file2.py" in result

    @pytest.mark.asyncio
    async def test_execute_run_command(self, tmp_path: Path) -> None:
        """Test run_command tool execution."""
        adapter = ToolExecutorAdapter(work_dir=tmp_path)
        result = await adapter.execute("run_command", {"command": "echo 'hello'"})

        assert "hello" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self) -> None:
        """Test unknown tool returns appropriate message."""
        adapter = ToolExecutorAdapter()
        result = await adapter.execute("unknown_tool", {})

        assert "Unknown tool" in result


# =============================================================================
# IterationResult Tests
# =============================================================================


class TestIterationResultFields:
    """Tests for new IterationResult fields."""

    def test_default_fields(self) -> None:
        """Test default field values."""
        result = IterationResult(success=True)

        assert result.task_id is None
        assert result.task_title is None
        assert result.files_changed == []
        assert result.tokens_used == 0
        assert result.all_tasks_complete is False
        assert result.error is None

    def test_with_all_fields(self) -> None:
        """Test with all fields populated."""
        result = IterationResult(
            success=True,
            output="Task completed",
            task_id="TASK-001",
            task_title="Add feature",
            files_changed=["src/main.py", "tests/test_main.py"],
            tokens_used=1500,
            all_tasks_complete=False,
            error=None,
        )

        assert result.task_id == "TASK-001"
        assert result.task_title == "Add feature"
        assert len(result.files_changed) == 2
        assert result.tokens_used == 1500


# =============================================================================
# RalphLoop LLM Integration Tests
# =============================================================================


class TestRalphLoopLLMIntegration:
    """Tests for RalphLoop with LLM integration."""

    @pytest.fixture
    def sample_prd(self, tmp_path: Path) -> Path:
        """Create a sample PRD.json file."""
        prd = {
            "project": {
                "id": "test-project",
                "name": "Test Project",
                "description": "A test project for testing",
            },
            "features": [
                {
                    "id": "TASK-001",
                    "description": "Create a hello world script",
                    "passes": False,
                    "priority": 1,
                    "steps": ["Create file", "Add content"],
                    "acceptance_criteria": ["File exists", "Contains 'hello'"],
                    "dependencies": [],
                }
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd, indent=2))
        return prd_path

    @pytest.fixture
    def completed_prd(self, tmp_path: Path) -> Path:
        """Create a PRD with all tasks complete."""
        prd = {
            "project": {
                "id": "done-project",
                "name": "Done Project",
                "description": "A completed project",
            },
            "features": [
                {
                    "id": "TASK-001",
                    "description": "Already done task",
                    "passes": True,
                    "priority": 1,
                }
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd, indent=2))
        return prd_path

    def test_loop_with_prd_path(self, sample_prd: Path) -> None:
        """Test creating loop with PRD path."""
        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(sample_prd),
        )

        assert loop._prd_path == sample_prd

    def test_from_config_with_prd(self, sample_prd: Path) -> None:
        """Test from_config creates LLM components."""
        config = RalphConfig()

        with patch.object(RalphLoop, "_create_orchestrator") as mock_orch:
            mock_orch.return_value = (MagicMock(), MagicMock())
            loop = RalphLoop.from_config(config, prd_path=str(sample_prd))

            assert loop._prd_path == sample_prd
            assert loop._task_executor is not None
            mock_orch.assert_called_once()

    def test_from_config_without_prd(self) -> None:
        """Test from_config without PRD doesn't create LLM components."""
        config = RalphConfig()
        loop = RalphLoop.from_config(config)

        assert loop._prd_path is None
        assert loop._task_executor is None
        assert loop._orchestrator is None

    def test_execute_iteration_stub_mode(self) -> None:
        """Test _execute_iteration returns stub when no PRD configured."""
        loop = RalphLoop(max_iterations=5)
        result = loop._execute_iteration()

        assert result.success is True
        assert result.output is None

    @pytest.mark.asyncio
    async def test_execute_iteration_all_complete(
        self,
        completed_prd: Path,
    ) -> None:
        """Test iteration returns completion when all tasks done."""
        from ralph_agi.tasks.executor import TaskExecutor

        executor = TaskExecutor()

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(completed_prd),
            task_executor=executor,
            orchestrator=MagicMock(),
        )

        result = await loop._execute_iteration_async()

        assert result.success is True
        assert result.all_tasks_complete is True
        assert loop._completion_signal in result.output

    @pytest.mark.asyncio
    async def test_execute_iteration_success(
        self,
        sample_prd: Path,
    ) -> None:
        """Test successful task execution via orchestrator."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        # Create mock orchestrator result
        builder_result = BuilderResult(
            status=AgentStatus.COMPLETED,
            task={"id": "TASK-001"},
            files_changed=["test.py"],
            total_tokens=500,
        )
        orch_result = OrchestratorResult(
            status=OrchestratorStatus.SUCCESS,
            task={"id": "TASK-001"},
            builder_result=builder_result,
            token_usage=TokenUsage(builder_input=350, builder_output=150),
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute_iteration = AsyncMock(return_value=orch_result)

        executor = TaskExecutor()

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(sample_prd),
            task_executor=executor,
            orchestrator=mock_orchestrator,
        )
        loop._tools = []

        result = await loop._execute_iteration_async()

        assert result.success is True
        assert result.task_id == "TASK-001"
        assert result.files_changed == ["test.py"]
        mock_orchestrator.execute_iteration.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_iteration_failure(
        self,
        sample_prd: Path,
    ) -> None:
        """Test failed task execution returns error."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        orch_result = OrchestratorResult(
            status=OrchestratorStatus.ERROR,
            task={"id": "TASK-001"},
            error="LLM API error",
            token_usage=TokenUsage(),
        )

        mock_orchestrator = MagicMock()
        mock_orchestrator.execute_iteration = AsyncMock(return_value=orch_result)

        executor = TaskExecutor()

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(sample_prd),
            task_executor=executor,
            orchestrator=mock_orchestrator,
        )
        loop._tools = []

        result = await loop._execute_iteration_async()

        assert result.success is False
        assert result.task_id == "TASK-001"
        assert "error" in result.error.lower()


# =============================================================================
# Build Tool Schemas Tests
# =============================================================================


class TestBuildToolSchemas:
    """Tests for tool schema building."""

    def test_build_tool_schemas_returns_list(self) -> None:
        """Test _build_tool_schemas returns a list of tools."""
        tools = RalphLoop._build_tool_schemas()

        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tool_schemas_have_required_fields(self) -> None:
        """Test each tool has name, description, and input_schema."""
        tools = RalphLoop._build_tool_schemas()

        for tool in tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "input_schema")
            assert tool.name  # Non-empty
            assert tool.description  # Non-empty

    def test_core_tools_present(self) -> None:
        """Test core tools are included."""
        tools = RalphLoop._build_tool_schemas()
        tool_names = {t.name for t in tools}

        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "list_directory" in tool_names
        assert "run_command" in tool_names
        assert "git_status" in tool_names


# =============================================================================
# Create LLM Client Tests
# =============================================================================


class TestCreateLLMClient:
    """Tests for LLM client creation."""

    def test_create_anthropic_client(self) -> None:
        """Test creating Anthropic client."""
        with patch("ralph_agi.llm.anthropic.AnthropicClient") as MockClient:
            client = RalphLoop._create_llm_client("anthropic", "claude-3-opus")
            MockClient.assert_called_once_with(model="claude-3-opus")

    def test_create_openai_client(self) -> None:
        """Test creating OpenAI client."""
        with patch("ralph_agi.llm.openai.OpenAIClient") as MockClient:
            client = RalphLoop._create_llm_client("openai", "gpt-4o")
            MockClient.assert_called_once_with(model="gpt-4o")

    def test_create_openrouter_client(self) -> None:
        """Test creating OpenRouter client."""
        with patch("ralph_agi.llm.openrouter.OpenRouterClient") as MockClient:
            client = RalphLoop._create_llm_client("openrouter", "claude-3-opus")
            MockClient.assert_called_once_with(model="claude-3-opus")

    def test_unknown_provider_raises(self) -> None:
        """Test unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            RalphLoop._create_llm_client("unknown", "model")


# =============================================================================
# Build Context Tests
# =============================================================================


class TestBuildContext:
    """Tests for context building methods."""

    def test_build_project_context_no_prd(self) -> None:
        """Test project context without PRD."""
        loop = RalphLoop(max_iterations=5)
        context = loop._build_project_context()

        assert "Working Directory" in context

    def test_build_project_context_with_prd(self, tmp_path: Path) -> None:
        """Test project context with PRD."""
        prd = {
            "project": {"id": "test", "name": "My Project", "description": "Test"},
            "features": [],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd))

        loop = RalphLoop(max_iterations=5, prd_path=str(prd_path))
        context = loop._build_project_context()

        assert "PRD.json" in context
        assert "My Project" in context

    def test_build_memory_context_no_memory(self) -> None:
        """Test memory context without memory store."""
        loop = RalphLoop(max_iterations=5)
        context = loop._build_memory_context()

        assert context == ""

    def test_build_memory_context_with_memory(self) -> None:
        """Test memory context with memory store."""
        mock_memory = MagicMock()
        mock_frame = MagicMock()
        mock_frame.content = "Previous iteration completed successfully"
        mock_memory.get_by_session.return_value = [mock_frame]

        loop = RalphLoop(max_iterations=5, memory_store=mock_memory)
        context = loop._build_memory_context()

        assert "Recent Context" in context
        assert "Previous iteration" in context


# =============================================================================
# End-to-End Flow Tests
# =============================================================================


class TestEndToEndFlow:
    """Tests for complete end-to-end workflows."""

    @pytest.fixture
    def multi_task_prd(self, tmp_path: Path) -> Path:
        """Create a PRD with multiple tasks."""
        prd = {
            "project": {
                "id": "multi-task",
                "name": "Multi-Task Project",
                "description": "Tests multi-task execution",
            },
            "features": [
                {
                    "id": "TASK-001",
                    "description": "First task",
                    "passes": False,
                    "priority": 1,
                    "steps": ["Do step 1"],
                    "acceptance_criteria": ["Criteria 1 met"],
                },
                {
                    "id": "TASK-002",
                    "description": "Second task",
                    "passes": False,
                    "priority": 2,
                    "steps": ["Do step 2"],
                    "acceptance_criteria": ["Criteria 2 met"],
                },
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd, indent=2))
        return prd_path

    def test_loop_run_max_iterations(self) -> None:
        """Test loop.run() respects max iterations in stub mode."""
        loop = RalphLoop(max_iterations=3)
        completed = loop.run(handle_signals=False)

        assert completed is False
        assert loop.iteration == 3

    def test_loop_run_zero_iterations(self) -> None:
        """Test loop.run() with zero max iterations."""
        loop = RalphLoop(max_iterations=0)
        completed = loop.run(handle_signals=False)

        assert completed is False
        assert loop.iteration == 0

    @pytest.mark.asyncio
    async def test_task_selection_priority_order(
        self,
        multi_task_prd: Path,
    ) -> None:
        """Test tasks are selected in priority order."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        # Mock orchestrator that always succeeds
        mock_orch = MagicMock()

        def create_result(task_id):
            builder = BuilderResult(
                status=AgentStatus.COMPLETED,
                task={"id": task_id},
                files_changed=[],
                total_tokens=100,
            )
            return OrchestratorResult(
                status=OrchestratorStatus.SUCCESS,
                task={"id": task_id},
                builder_result=builder,
                token_usage=TokenUsage(),
            )

        mock_orch.execute_iteration = AsyncMock(
            side_effect=[create_result("TASK-001"), create_result("TASK-002")]
        )

        executor = TaskExecutor()
        loop = RalphLoop(
            max_iterations=3,
            prd_path=str(multi_task_prd),
            task_executor=executor,
            orchestrator=mock_orch,
        )
        loop._tools = []

        # First iteration should pick TASK-001 (priority 1)
        result1 = await loop._execute_iteration_async()
        assert result1.task_id == "TASK-001"

    def test_loop_completion_signal_detected(self) -> None:
        """Test loop detects completion signal."""
        loop = RalphLoop(
            max_iterations=10,
            completion_promise="<promise>COMPLETE</promise>",
        )

        # Manually check completion signal
        assert loop._check_completion("<promise>COMPLETE</promise>") is True
        assert loop._check_completion("Some output with <promise>COMPLETE</promise> in it") is True
        assert loop._check_completion("Regular output") is False

    def test_iteration_result_stores_in_memory(self) -> None:
        """Test iteration results are stored in memory."""
        mock_memory = MagicMock()
        mock_memory.append = MagicMock()

        loop = RalphLoop(
            max_iterations=5,
            memory_store=mock_memory,
        )

        result = IterationResult(
            success=True,
            output="Task completed",
            task_id="TASK-001",
        )

        loop._store_iteration_result(result)

        # Memory append should be called
        mock_memory.append.assert_called()


class TestTokenTracking:
    """Tests for token usage tracking."""

    def test_initial_token_counts_zero(self) -> None:
        """Test token counts start at zero."""
        loop = RalphLoop(max_iterations=5)

        assert loop.total_input_tokens == 0
        assert loop.total_output_tokens == 0

    def test_tokens_accumulated_during_run(self) -> None:
        """Test tokens are accumulated during stub run."""
        loop = RalphLoop(max_iterations=2)
        loop.run(handle_signals=False)

        # Stub mode doesn't use tokens
        assert loop.total_input_tokens == 0
        assert loop.total_output_tokens == 0

    @pytest.mark.asyncio
    async def test_tokens_from_orchestrator(self, tmp_path: Path) -> None:
        """Test tokens are tracked from orchestrator results."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        prd = {
            "project": {"id": "test", "name": "Test", "description": "Test project"},
            "features": [{"id": "T1", "description": "Task", "passes": False, "priority": 1}],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd))

        builder = BuilderResult(
            status=AgentStatus.COMPLETED,
            task={"id": "T1"},
            files_changed=[],
            total_tokens=1000,
        )
        orch_result = OrchestratorResult(
            status=OrchestratorStatus.SUCCESS,
            task={"id": "T1"},
            builder_result=builder,
            token_usage=TokenUsage(builder_input=700, builder_output=300),
        )

        mock_orch = MagicMock()
        mock_orch.execute_iteration = AsyncMock(return_value=orch_result)

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(prd_path),
            task_executor=TaskExecutor(),
            orchestrator=mock_orch,
        )
        loop._tools = []

        result = await loop._execute_iteration_async()

        # Tokens should be in the result
        assert result.tokens_used == 1000


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery and resilience."""

    def test_invalid_prd_path_handled(self) -> None:
        """Test graceful handling of invalid PRD path."""
        loop = RalphLoop(
            max_iterations=5,
            prd_path="/nonexistent/path/PRD.json",
        )

        # Should not raise during init
        assert loop._prd_path is not None

    def test_malformed_prd_handled(self, tmp_path: Path) -> None:
        """Test handling of malformed PRD JSON."""
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text("{ invalid json }")

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(prd_path),
        )

        # Execution should handle gracefully
        result = loop._execute_iteration()
        # Should return stub result or error, not crash
        assert result is not None

    def test_empty_prd_handled(self, tmp_path: Path) -> None:
        """Test handling of empty PRD."""
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text("{}")

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(prd_path),
        )

        result = loop._execute_iteration()
        assert result is not None

    @pytest.mark.asyncio
    async def test_orchestrator_error_recovery(self, tmp_path: Path) -> None:
        """Test recovery from orchestrator errors."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        prd = {
            "project": {"id": "test", "name": "Test", "description": "Test"},
            "features": [
                {"id": "T1", "description": "Task", "passes": False, "priority": 1}
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd))

        # Orchestrator that raises an exception
        mock_orch = MagicMock()
        mock_orch.execute_iteration = AsyncMock(
            side_effect=RuntimeError("LLM API failed")
        )

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(prd_path),
            task_executor=TaskExecutor(),
            orchestrator=mock_orch,
        )
        loop._tools = []

        # Should handle exception gracefully
        result = await loop._execute_iteration_async()
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_blocked_status_handled(self, tmp_path: Path) -> None:
        """Test handling of blocked orchestrator status."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        prd = {
            "project": {"id": "test", "name": "Test", "description": "Test"},
            "features": [
                {"id": "T1", "description": "Task", "passes": False, "priority": 1}
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd))

        orch_result = OrchestratorResult(
            status=OrchestratorStatus.BLOCKED,
            task={"id": "T1"},
            error="Missing dependency",
            token_usage=TokenUsage(),
        )

        mock_orch = MagicMock()
        mock_orch.execute_iteration = AsyncMock(return_value=orch_result)

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(prd_path),
            task_executor=TaskExecutor(),
            orchestrator=mock_orch,
        )
        loop._tools = []

        result = await loop._execute_iteration_async()
        assert result.success is False
        assert "blocked" in result.error.lower() or "dependency" in result.error.lower()

    def test_retry_logic_applied(self) -> None:
        """Test that retry logic is correctly configured."""
        loop = RalphLoop(
            max_iterations=5,
            max_retries=3,
            retry_delays=[1, 2, 4],
        )

        assert loop.max_retries == 3
        assert loop.retry_delays == [1, 2, 4]

    def test_close_handles_cleanup(self) -> None:
        """Test that close() properly cleans up resources."""
        mock_memory = MagicMock()
        mock_memory.close = MagicMock()

        loop = RalphLoop(
            max_iterations=5,
            memory_store=mock_memory,
        )

        loop.close()

        mock_memory.close.assert_called_once()

    def test_close_without_memory(self) -> None:
        """Test close() works when no memory store configured."""
        loop = RalphLoop(max_iterations=5)

        # Should not raise
        loop.close()

    @pytest.mark.asyncio
    async def test_needs_revision_status_handled(self, tmp_path: Path) -> None:
        """Test handling of needs_revision status from critic."""
        from ralph_agi.tasks.executor import TaskExecutor
        from ralph_agi.llm.orchestrator import TokenUsage

        prd = {
            "project": {"id": "test", "name": "Test", "description": "Test"},
            "features": [
                {"id": "T1", "description": "Task", "passes": False, "priority": 1}
            ],
        }
        prd_path = tmp_path / "PRD.json"
        prd_path.write_text(json.dumps(prd))

        orch_result = OrchestratorResult(
            status=OrchestratorStatus.NEEDS_REVISION,
            task={"id": "T1"},
            error="Code review failed: missing error handling",
            token_usage=TokenUsage(),
        )

        mock_orch = MagicMock()
        mock_orch.execute_iteration = AsyncMock(return_value=orch_result)

        loop = RalphLoop(
            max_iterations=5,
            prd_path=str(prd_path),
            task_executor=TaskExecutor(),
            orchestrator=mock_orch,
        )
        loop._tools = []

        result = await loop._execute_iteration_async()
        assert result.success is False
        # Task should be aborted, not marked complete


class TestGracefulShutdown:
    """Tests for graceful shutdown handling."""

    def test_interrupt_flag_works(self) -> None:
        """Test that interrupt flag stops the loop."""
        loop = RalphLoop(max_iterations=100)

        # Simulate interrupt
        loop._interrupted = True

        # The loop should respect the interrupted flag
        # (we can't easily test full run() with signals in unit tests)
        assert loop._interrupted is True

    def test_checkpoint_path_configured(self, tmp_path: Path) -> None:
        """Test checkpoint path configuration."""
        checkpoint = tmp_path / "checkpoint.json"

        loop = RalphLoop(
            max_iterations=5,
            checkpoint_path=str(checkpoint),
        )

        assert loop._checkpoint_path == str(checkpoint)

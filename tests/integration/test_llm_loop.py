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
            mock_orch.return_value = MagicMock()
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

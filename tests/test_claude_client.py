"""Unit tests for Claude CLI client module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from resume_generator.claude_client import (
    CLAUDE_BINARY,
    DEFAULT_TIMEOUT,
    ClaudeCLI,
    ClaudeCLIError,
    ClaudeCLIInvocationError,
    ClaudeCLINotFoundError,
    InvokeResult,
    build_prompt_with_schema,
    parse_json_response,
)


class TestInvokeResult:
    """Tests for InvokeResult dataclass."""

    def test_successful_result(self) -> None:
        result = InvokeResult(success=True, output="success output", exit_code=0)
        assert result.success is True
        assert result.failed is False
        assert result.output == "success output"
        assert result.exit_code == 0

    def test_failed_result(self) -> None:
        result = InvokeResult(success=False, output="error output", exit_code=1)
        assert result.success is False
        assert result.failed is True
        assert result.output == "error output"
        assert result.exit_code == 1

    def test_result_is_immutable(self) -> None:
        result = InvokeResult(success=True, output="test", exit_code=0)
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


class TestClaudeCLI:
    """Tests for ClaudeCLI class."""

    def test_init_default_values(self) -> None:
        cli = ClaudeCLI()
        assert cli.model == "sonnet"
        assert cli.timeout == DEFAULT_TIMEOUT

    def test_init_custom_values(self) -> None:
        cli = ClaudeCLI(model="opus", timeout=1800)
        assert cli.model == "opus"
        assert cli.timeout == 1800

    def test_init_haiku_model(self) -> None:
        cli = ClaudeCLI(model="haiku")
        assert cli.model == "haiku"

    @patch("shutil.which")
    def test_available_when_binary_exists(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/local/bin/claude"
        assert ClaudeCLI.available() is True
        mock_which.assert_called_once_with(CLAUDE_BINARY)

    @patch("shutil.which")
    def test_available_when_binary_not_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        assert ClaudeCLI.available() is False

    @patch("subprocess.run")
    def test_version_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="claude 1.2.3\n", stderr="")
        version = ClaudeCLI.version()
        assert version == "claude 1.2.3"
        mock_run.assert_called_once_with(
            [CLAUDE_BINARY, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    @patch("subprocess.run")
    def test_version_from_stderr(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="", stderr="claude 1.2.3")
        version = ClaudeCLI.version()
        assert version == "claude 1.2.3"

    @patch("subprocess.run")
    def test_version_when_not_installed(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError()
        version = ClaudeCLI.version()
        assert version == ""

    @patch("subprocess.run")
    def test_version_on_timeout(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)
        version = ClaudeCLI.version()
        assert version == ""

    def test_build_args_basic(self) -> None:
        cli = ClaudeCLI(model="sonnet")
        args = cli._build_args()
        assert args == [
            CLAUDE_BINARY,
            "-p",
            "--dangerously-skip-permissions",
            "--model",
            "sonnet",
        ]

    def test_build_args_with_system_prompt(self) -> None:
        cli = ClaudeCLI(model="opus")
        args = cli._build_args(system="You are a helpful assistant")
        assert args == [
            CLAUDE_BINARY,
            "-p",
            "--dangerously-skip-permissions",
            "--model",
            "opus",
            "--system-prompt",
            "You are a helpful assistant",
        ]

    @patch("os.environ.get")
    def test_should_use_pty_respects_env_var(self, mock_env: MagicMock) -> None:
        mock_env.return_value = "1"
        cli = ClaudeCLI()
        assert cli._should_use_pty() is False

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_success(self, mock_popen: MagicMock, mock_use_pty: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.stdout = iter(["Line 1\n", "Line 2\n"])
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        cli = ClaudeCLI()
        result = cli.invoke("test prompt")

        assert result.success is True
        assert result.exit_code == 0
        assert "Line 1" in result.output
        assert "Line 2" in result.output

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_failure(self, mock_popen: MagicMock, mock_use_pty: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.stdout = iter(["Error occurred\n"])
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        cli = ClaudeCLI()
        result = cli.invoke("test prompt")

        assert result.success is False
        assert result.failed is True
        assert result.exit_code == 1

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_with_system_prompt(
        self, mock_popen: MagicMock, mock_use_pty: MagicMock
    ) -> None:
        mock_process = MagicMock()
        mock_process.stdout = iter(["output\n"])
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        cli = ClaudeCLI()
        cli.invoke("prompt", system="system prompt")

        call_args = mock_popen.call_args[0][0]
        assert "--system-prompt" in call_args
        assert "system prompt" in call_args

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_with_working_dir(
        self, mock_popen: MagicMock, mock_use_pty: MagicMock, tmp_path: Path
    ) -> None:
        mock_process = MagicMock()
        mock_process.stdout = iter(["output\n"])
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        cli = ClaudeCLI()
        cli.invoke("prompt", working_dir=tmp_path)

        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs["cwd"] == str(tmp_path)

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_timeout(self, mock_popen: MagicMock, mock_use_pty: MagicMock) -> None:
        mock_process = MagicMock()
        mock_process.stdout = iter(["partial output\n"])
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 60)
        mock_popen.return_value = mock_process

        cli = ClaudeCLI(timeout=60)
        result = cli.invoke("test prompt")

        assert result.success is False
        assert result.exit_code == -1
        assert "TIMEOUT" in result.output
        mock_process.kill.assert_called_once()

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_not_found_error(self, mock_popen: MagicMock, mock_use_pty: MagicMock) -> None:
        mock_popen.side_effect = FileNotFoundError()

        cli = ClaudeCLI()
        with pytest.raises(ClaudeCLINotFoundError) as exc_info:
            cli.invoke("test prompt")

        assert "not found" in str(exc_info.value).lower()

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_os_error(self, mock_popen: MagicMock, mock_use_pty: MagicMock) -> None:
        mock_popen.side_effect = OSError("Permission denied")

        cli = ClaudeCLI()
        with pytest.raises(ClaudeCLIInvocationError) as exc_info:
            cli.invoke("test prompt")

        assert "Permission denied" in str(exc_info.value)

    @patch.object(ClaudeCLI, "_should_use_pty", return_value=False)
    @patch("subprocess.Popen")
    def test_invoke_shows_progress_for_tool_usage(
        self, mock_popen: MagicMock, mock_use_pty: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_process = MagicMock()
        mock_process.stdout = iter(["[Tool: Read] reading file\n", "[Tool: Write] writing\n"])
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        cli = ClaudeCLI()
        cli.invoke("test prompt")

        captured = capsys.readouterr()
        assert ".." in captured.out


class TestParseJsonResponse:
    """Tests for parse_json_response function."""

    def test_parse_raw_json(self) -> None:
        response = '{"name": "test", "value": 123}'
        result = parse_json_response(response)
        assert result == {"name": "test", "value": 123}

    def test_parse_json_with_whitespace(self) -> None:
        response = '  \n  {"key": "value"}\n  '
        result = parse_json_response(response)
        assert result == {"key": "value"}

    def test_parse_json_in_code_block(self) -> None:
        response = """```json
{"name": "test"}
```"""
        result = parse_json_response(response)
        assert result == {"name": "test"}

    def test_parse_json_in_code_block_no_language(self) -> None:
        response = """```
{"name": "test"}
```"""
        result = parse_json_response(response)
        assert result == {"name": "test"}

    def test_parse_json_with_surrounding_text(self) -> None:
        response = """Here is the result:
{"status": "success", "count": 5}
That's all."""
        result = parse_json_response(response)
        assert result == {"status": "success", "count": 5}

    def test_parse_nested_json(self) -> None:
        response = '{"outer": {"inner": "value"}, "list": [1, 2, 3]}'
        result = parse_json_response(response)
        assert result == {"outer": {"inner": "value"}, "list": [1, 2, 3]}

    def test_parse_invalid_json_raises_error(self) -> None:
        response = "This is not JSON at all"
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            parse_json_response(response)

    def test_parse_malformed_json_raises_error(self) -> None:
        response = '{"key": value without quotes}'
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            parse_json_response(response)

    def test_parse_empty_response_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            parse_json_response("")

    def test_parse_json_array_in_response(self) -> None:
        response = 'Result: {"items": [1, 2, 3]}'
        result = parse_json_response(response)
        assert result == {"items": [1, 2, 3]}


class TestBuildPromptWithSchema:
    """Tests for build_prompt_with_schema function."""

    def test_build_simple_prompt(self) -> None:
        class SimpleSchema(BaseModel):
            name: str
            value: int

        prompt = build_prompt_with_schema("Extract data", SimpleSchema)

        assert "Extract data" in prompt
        assert "IMPORTANT" in prompt
        assert "JSON" in prompt
        assert '"name"' in prompt
        assert '"value"' in prompt

    def test_build_prompt_with_nested_schema(self) -> None:
        class Inner(BaseModel):
            field: str

        class Outer(BaseModel):
            inner: Inner
            items: list[str]

        prompt = build_prompt_with_schema("Process this", Outer)

        assert "Process this" in prompt
        assert '"inner"' in prompt
        assert '"items"' in prompt

    def test_prompt_instructs_json_only(self) -> None:
        class Schema(BaseModel):
            data: str

        prompt = build_prompt_with_schema("Test", Schema)

        assert "ONLY valid JSON" in prompt
        assert "Do not include any explanation" in prompt


class TestClaudeCLIExceptions:
    """Tests for Claude CLI exception hierarchy."""

    def test_exception_hierarchy(self) -> None:
        assert issubclass(ClaudeCLINotFoundError, ClaudeCLIError)
        assert issubclass(ClaudeCLIInvocationError, ClaudeCLIError)
        assert issubclass(ClaudeCLIError, Exception)

    def test_not_found_error_message(self) -> None:
        error = ClaudeCLINotFoundError("Claude CLI not found")
        assert "Claude CLI not found" in str(error)

    def test_invocation_error_message(self) -> None:
        error = ClaudeCLIInvocationError("Failed to execute")
        assert "Failed to execute" in str(error)

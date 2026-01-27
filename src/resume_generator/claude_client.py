"""Claude CLI client for subprocess-based Claude invocation."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

CLAUDE_BINARY = "claude"
DEFAULT_TIMEOUT = 3600


@dataclass(frozen=True)
class InvokeResult:
    """Result of a Claude CLI invocation."""

    success: bool
    output: str
    exit_code: int

    @property
    def failed(self) -> bool:
        return not self.success


class ClaudeCLIError(Exception):
    """Base exception for Claude CLI errors."""


class ClaudeCLINotFoundError(ClaudeCLIError):
    """Raised when Claude CLI binary is not found."""


class ClaudeCLITimeoutError(ClaudeCLIError):
    """Raised when Claude CLI invocation times out."""


class ClaudeCLIInvocationError(ClaudeCLIError):
    """Raised when Claude CLI invocation fails."""


class ClaudeCLI:
    """Wrapper around the Claude Code CLI for subprocess-based invocation."""

    def __init__(self, model: str = "sonnet", timeout: int = DEFAULT_TIMEOUT) -> None:
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    @property
    def timeout(self) -> int:
        return self._timeout

    @staticmethod
    def available() -> bool:
        """Check if Claude CLI is available on the system."""
        return shutil.which(CLAUDE_BINARY) is not None

    @staticmethod
    def version() -> str:
        """Get Claude CLI version string."""
        try:
            result = subprocess.run(
                [CLAUDE_BINARY, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            return ""

    def invoke(
        self,
        prompt: str,
        system: str | None = None,
        working_dir: Path | None = None,
    ) -> InvokeResult:
        """Invoke Claude CLI with a prompt.

        Args:
            prompt: The prompt to send to Claude.
            system: Optional system prompt.
            working_dir: Optional working directory for the subprocess.

        Returns:
            InvokeResult containing success status, output, and exit code.
        """
        args = self._build_args(system)
        cwd = str(working_dir) if working_dir else None

        output_lines: list[str] = []
        exit_code = -1
        success = False

        try:
            if self._should_use_pty():
                success, exit_code = self._invoke_with_pty(args, prompt, output_lines, cwd)
            else:
                success, exit_code = self._invoke_with_subprocess(args, prompt, output_lines, cwd)
        except subprocess.TimeoutExpired:
            output_lines.append(f"\n[TIMEOUT after {self._timeout}s]")
            return InvokeResult(success=False, output="".join(output_lines), exit_code=-1)
        except FileNotFoundError as e:
            raise ClaudeCLINotFoundError(
                f"Claude CLI binary '{CLAUDE_BINARY}' not found. "
                "Please install Claude CLI first."
            ) from e
        except OSError as e:
            raise ClaudeCLIInvocationError(f"Failed to invoke Claude CLI: {e}") from e

        return InvokeResult(success=success, output="".join(output_lines), exit_code=exit_code)

    def _build_args(self, system: str | None = None) -> list[str]:
        """Build command line arguments for Claude CLI."""
        args = [
            CLAUDE_BINARY,
            "-p",
            "--dangerously-skip-permissions",
            "--model",
            self._model,
        ]
        if system:
            args.extend(["--system-prompt", system])
        return args

    def _should_use_pty(self) -> bool:
        """Determine whether to use PTY or regular subprocess."""
        if os.environ.get("CLAUDE_CLI_USE_SUBPROCESS"):
            return False
        if sys.platform == "win32":
            return False
        try:
            import pty as _pty  # noqa: F401

            return True
        except ImportError:
            return False

    def _invoke_with_pty(
        self,
        args: list[str],
        prompt: str,
        output_lines: list[str],
        cwd: str | None,
    ) -> tuple[bool, int]:
        """Invoke using PTY for real-time output."""
        import pty

        pid, fd = pty.fork()

        if pid == 0:
            if cwd:
                os.chdir(cwd)
            os.execvp(args[0], args + [prompt])

        try:
            self._stream_pty_output(fd, output_lines)
        finally:
            os.close(fd)

        _, status = os.waitpid(pid, 0)
        exit_code = os.waitstatus_to_exitcode(status)
        return exit_code == 0, exit_code

    def _stream_pty_output(self, fd: int, output_lines: list[str]) -> None:
        """Stream output from PTY file descriptor."""
        import select

        while True:
            readable, _, _ = select.select([fd], [], [], 1.0)
            if not readable:
                try:
                    os.waitpid(-1, os.WNOHANG)
                except ChildProcessError:
                    break
                continue
            try:
                data = os.read(fd, 4096)
                if not data:
                    break
                decoded = data.decode("utf-8", errors="replace")
                output_lines.append(decoded)
                self._show_progress(decoded)
            except OSError:
                break

    def _invoke_with_subprocess(
        self,
        args: list[str],
        prompt: str,
        output_lines: list[str],
        cwd: str | None,
    ) -> tuple[bool, int]:
        """Invoke using subprocess.Popen."""
        process = subprocess.Popen(
            args + [prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
        )

        try:
            for line in self._read_process_output(process):
                output_lines.append(line)
                self._show_progress(line)

            process.wait(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            raise

        exit_code = process.returncode
        return exit_code == 0, exit_code

    def _read_process_output(self, process: subprocess.Popen[str]) -> Iterator[str]:
        """Read output from process stdout."""
        if process.stdout is None:
            return
        yield from process.stdout

    def _show_progress(self, text: str) -> None:
        """Show progress indicator for tool usage."""
        if "[Tool:" in text:
            sys.stdout.write(".")
            sys.stdout.flush()


def parse_json_response(response: str) -> dict[str, object]:
    """Extract and parse JSON from Claude's response.

    Handles responses that may contain:
    - Raw JSON
    - JSON wrapped in markdown code blocks (```json ... ```)
    - JSON with surrounding text

    Args:
        response: The raw response string from Claude.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        ValueError: If no valid JSON can be extracted.
    """
    text = response.strip()

    if text.startswith("```"):
        text = _extract_from_code_block(text)

    try:
        parsed: dict[str, object] = json.loads(text)
        return parsed
    except json.JSONDecodeError:
        pass

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")


def _extract_from_code_block(text: str) -> str:
    """Extract content from markdown code block."""
    lines = text.split("\n")
    start_idx = 1
    end_idx = len(lines)

    for i, line in enumerate(lines[1:], 1):
        if line.startswith("```"):
            end_idx = i
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


def build_prompt_with_schema(user_prompt: str, schema: type[BaseModel]) -> str:
    """Build a prompt that requests JSON output matching a Pydantic schema.

    Args:
        user_prompt: The user's prompt/request.
        schema: A Pydantic model class defining the expected output structure.

    Returns:
        A formatted prompt that instructs Claude to return JSON.
    """
    schema_json = json.dumps(schema.model_json_schema(), indent=2)

    return f"""{user_prompt}

IMPORTANT: You MUST respond with ONLY valid JSON that matches this schema:

```json
{schema_json}
```

Do not include any explanation or text outside the JSON. Return only the JSON object."""

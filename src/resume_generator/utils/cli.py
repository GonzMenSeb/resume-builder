"""CLI utility functions for Claude CLI operations."""

from __future__ import annotations

from resume_generator.claude_client import ClaudeCLI


def check_claude_available() -> bool:
    """Check if Claude CLI is available on the system.

    Returns:
        True if the `claude` binary is found in PATH, False otherwise.
    """
    return ClaudeCLI.available()


def get_claude_version() -> str:
    """Get the installed Claude CLI version string.

    Returns:
        Version string from `claude --version`, or empty string if unavailable.
    """
    return ClaudeCLI.version()


def require_claude_cli() -> None:
    """Ensure Claude CLI is available, raising an error if not.

    Raises:
        RuntimeError: If Claude CLI is not found on the system.
    """
    if not check_claude_available():
        raise RuntimeError(
            "Claude CLI is not installed or not in PATH. "
            "Please install Claude CLI to use this application. "
            "Visit https://claude.ai/docs/cli for installation instructions."
        )

"""JSON parsing utilities for Claude CLI responses."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class JSONParseError(ValueError):
    """Raised when JSON extraction or parsing fails."""


class JSONValidationError(ValueError):
    """Raised when JSON validation against a schema fails."""

    def __init__(self, message: str, validation_error: ValidationError | None = None) -> None:
        super().__init__(message)
        self.validation_error = validation_error


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
        JSONParseError: If no valid JSON can be extracted.
    """
    text = response.strip()

    if text.startswith("```"):
        text = extract_json_from_markdown(text)

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

    raise JSONParseError(f"Could not extract valid JSON from response: {text[:200]}...")


def extract_json_from_markdown(text: str) -> str:
    """Extract content from markdown code block.

    Handles code blocks in the format:
    ```json
    { ... }
    ```

    or:
    ```
    { ... }
    ```

    Args:
        text: Text containing a markdown code block.

    Returns:
        The content inside the code block with fences removed.
    """
    lines = text.strip().split("\n")

    if not lines or not lines[0].startswith("```"):
        return text

    start_idx = 1
    end_idx = len(lines)

    for i, line in enumerate(lines[1:], 1):
        if line.startswith("```"):
            end_idx = i
            break

    return "\n".join(lines[start_idx:end_idx]).strip()


def validate_json_against_schema(data: dict[str, Any], schema: type[T]) -> T:
    """Validate a dictionary against a Pydantic schema and return the model instance.

    Args:
        data: Dictionary to validate.
        schema: Pydantic model class to validate against.

    Returns:
        Validated Pydantic model instance.

    Raises:
        JSONValidationError: If validation fails.
    """
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        raise JSONValidationError(
            f"JSON validation failed for schema {schema.__name__}: {e}",
            validation_error=e,
        ) from e


def parse_and_validate(response: str, schema: type[T]) -> T:
    """Parse JSON from response and validate against a Pydantic schema.

    Convenience function combining parse_json_response and validate_json_against_schema.

    Args:
        response: The raw response string from Claude.
        schema: Pydantic model class to validate against.

    Returns:
        Validated Pydantic model instance.

    Raises:
        JSONParseError: If no valid JSON can be extracted.
        JSONValidationError: If validation fails.
    """
    data = parse_json_response(response)
    return validate_json_against_schema(data, schema)

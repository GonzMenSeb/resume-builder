"""Unit tests for JSON parsing utilities."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from resume_generator.utils.json_parser import (
    JSONParseError,
    JSONValidationError,
    extract_json_from_markdown,
    parse_and_validate,
    parse_json_response,
    validate_json_against_schema,
)


class SampleSchema(BaseModel):
    name: str
    value: int


class NestedSchema(BaseModel):
    inner: SampleSchema
    items: list[str]


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
        with pytest.raises(JSONParseError, match="Could not extract valid JSON"):
            parse_json_response(response)

    def test_parse_malformed_json_raises_error(self) -> None:
        response = '{"key": value without quotes}'
        with pytest.raises(JSONParseError, match="Could not extract valid JSON"):
            parse_json_response(response)

    def test_parse_empty_response_raises_error(self) -> None:
        with pytest.raises(JSONParseError, match="Could not extract valid JSON"):
            parse_json_response("")

    def test_parse_json_array_in_response(self) -> None:
        response = 'Result: {"items": [1, 2, 3]}'
        result = parse_json_response(response)
        assert result == {"items": [1, 2, 3]}


class TestExtractJsonFromMarkdown:
    """Tests for extract_json_from_markdown function."""

    def test_extract_from_json_code_block(self) -> None:
        text = """```json
{"key": "value"}
```"""
        result = extract_json_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_from_plain_code_block(self) -> None:
        text = """```
{"key": "value"}
```"""
        result = extract_json_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_multiline_content(self) -> None:
        text = """```json
{
    "key": "value",
    "number": 42
}
```"""
        result = extract_json_from_markdown(text)
        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_returns_original_if_no_code_block(self) -> None:
        text = '{"key": "value"}'
        result = extract_json_from_markdown(text)
        assert result == text

    def test_handles_empty_string(self) -> None:
        result = extract_json_from_markdown("")
        assert result == ""


class TestValidateJsonAgainstSchema:
    """Tests for validate_json_against_schema function."""

    def test_validate_valid_data(self) -> None:
        data = {"name": "test", "value": 123}
        result = validate_json_against_schema(data, SampleSchema)
        assert isinstance(result, SampleSchema)
        assert result.name == "test"
        assert result.value == 123

    def test_validate_nested_data(self) -> None:
        data = {"inner": {"name": "nested", "value": 42}, "items": ["a", "b"]}
        result = validate_json_against_schema(data, NestedSchema)
        assert isinstance(result, NestedSchema)
        assert result.inner.name == "nested"
        assert result.items == ["a", "b"]

    def test_validate_missing_field_raises_error(self) -> None:
        data = {"name": "test"}
        with pytest.raises(JSONValidationError) as exc_info:
            validate_json_against_schema(data, SampleSchema)
        assert "SampleSchema" in str(exc_info.value)
        assert exc_info.value.validation_error is not None

    def test_validate_wrong_type_raises_error(self) -> None:
        data = {"name": "test", "value": "not an int"}
        with pytest.raises(JSONValidationError):
            validate_json_against_schema(data, SampleSchema)


class TestParseAndValidate:
    """Tests for parse_and_validate convenience function."""

    def test_parse_and_validate_success(self) -> None:
        response = '{"name": "test", "value": 42}'
        result = parse_and_validate(response, SampleSchema)
        assert isinstance(result, SampleSchema)
        assert result.name == "test"
        assert result.value == 42

    def test_parse_and_validate_from_code_block(self) -> None:
        response = """```json
{"name": "test", "value": 99}
```"""
        result = parse_and_validate(response, SampleSchema)
        assert result.value == 99

    def test_parse_and_validate_invalid_json(self) -> None:
        response = "not json"
        with pytest.raises(JSONParseError):
            parse_and_validate(response, SampleSchema)

    def test_parse_and_validate_invalid_schema(self) -> None:
        response = '{"wrong": "fields"}'
        with pytest.raises(JSONValidationError):
            parse_and_validate(response, SampleSchema)


class TestExceptionClasses:
    """Tests for custom exception classes."""

    def test_json_parse_error_is_value_error(self) -> None:
        assert issubclass(JSONParseError, ValueError)

    def test_json_validation_error_is_value_error(self) -> None:
        assert issubclass(JSONValidationError, ValueError)

    def test_json_validation_error_stores_original(self) -> None:
        from pydantic import ValidationError

        try:
            SampleSchema(name="test")  # type: ignore[call-arg]
        except ValidationError as e:
            error = JSONValidationError("test", validation_error=e)
            assert error.validation_error is e

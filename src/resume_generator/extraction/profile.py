"""Profile extraction using Claude to parse raw text into structured PersonProfile."""

import json
import logging
from typing import Any

from anthropic import Anthropic
from pydantic import ValidationError

from resume_generator.config import Settings, get_settings
from resume_generator.extraction.prompts import (
    PROFILE_EXTRACTION_SYSTEM,
    build_profile_extraction_prompt,
)
from resume_generator.models.profile import PersonProfile

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when profile extraction fails."""


class ProfileExtractor:
    """Extracts structured PersonProfile from raw text using Claude."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = Anthropic(api_key=self._settings.anthropic_api_key.get_secret_value())

    def extract(self, raw_text: str) -> PersonProfile:
        """Extract a PersonProfile from raw text.

        Args:
            raw_text: Unstructured text containing person's professional info.

        Returns:
            Parsed and validated PersonProfile.

        Raises:
            ExtractionError: If extraction or parsing fails.
        """
        if not raw_text.strip():
            raise ExtractionError("Cannot extract profile from empty text")

        user_prompt = build_profile_extraction_prompt(raw_text)
        response_text = self._call_claude(user_prompt)
        profile = self._parse_response(response_text, raw_text)
        return profile

    def _call_claude(self, user_prompt: str) -> str:
        """Call Claude API and return the response text."""
        try:
            response = self._client.messages.create(
                model=self._settings.claude_model.value,
                max_tokens=self._settings.max_tokens,
                system=PROFILE_EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = response.content[0]
            if content.type != "text":
                raise ExtractionError(f"Unexpected response type: {content.type}")
            return content.text
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            logger.exception("Claude API call failed")
            raise ExtractionError(f"API call failed: {e}") from e

    def _parse_response(self, response_text: str, original_text: str) -> PersonProfile:
        """Parse Claude's JSON response into PersonProfile."""
        json_str = self._extract_json(response_text)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ExtractionError(f"Invalid JSON in response: {e}") from e

        data["raw_text"] = original_text
        return self._validate_profile(data)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = 1
            end = len(lines)
            for i, line in enumerate(lines[1:], 1):
                if line.startswith("```"):
                    end = i
                    break
            text = "\n".join(lines[start:end])
        return text.strip()

    def _validate_profile(self, data: dict[str, Any]) -> PersonProfile:
        """Validate and construct PersonProfile from dict."""
        try:
            return PersonProfile.model_validate(data)
        except ValidationError as e:
            logger.error("Profile validation failed: %s", e)
            raise ExtractionError(f"Profile validation failed: {e}") from e

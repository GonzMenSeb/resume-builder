"""Unit tests for extraction module."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from anthropic import APIConnectionError, APITimeoutError, RateLimitError
from anthropic.types.beta import BetaUsage
from anthropic.types.beta.parsed_beta_message import ParsedBetaMessage, ParsedBetaTextBlock
from pydantic import SecretStr

from resume_generator.config import Settings
from resume_generator.extraction.profile import (
    ContactInfoSchema,
    EducationSchema,
    ExperienceSchema,
    ExtractionError,
    ProfileExtractionSchema,
    ProfileExtractor,
    SkillSchema,
    _call_with_retry,
    _exponential_backoff,
    _is_retryable_error,
)
from resume_generator.models.profile import (
    PersonProfile,
    SkillCategory,
)


class TestRetryHelpers:
    """Tests for retry helper functions."""

    def test_is_retryable_error_timeout(self) -> None:
        mock_request = MagicMock()
        error = APITimeoutError(request=mock_request)
        assert _is_retryable_error(error)

    def test_is_retryable_error_connection(self) -> None:
        mock_request = MagicMock()
        error = APIConnectionError(message="connection", request=mock_request)
        assert _is_retryable_error(error)

    def test_is_retryable_error_rate_limit(self) -> None:
        mock_response = MagicMock()
        error = RateLimitError("rate limit", response=mock_response, body=None)
        assert _is_retryable_error(error)

    def test_is_retryable_error_generic_exception(self) -> None:
        assert not _is_retryable_error(ValueError("not retryable"))

    def test_exponential_backoff_initial(self) -> None:
        backoff = _exponential_backoff(0)
        assert backoff == 1.0

    def test_exponential_backoff_second_attempt(self) -> None:
        backoff = _exponential_backoff(1)
        assert backoff == 2.0

    def test_exponential_backoff_caps_at_max(self) -> None:
        backoff = _exponential_backoff(10)
        assert backoff == 32.0

    def test_call_with_retry_success_first_attempt(self) -> None:
        mock_func = MagicMock(return_value="success")
        result = _call_with_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_call_with_retry_success_after_retries(self) -> None:
        mock_request = MagicMock()
        mock_func = MagicMock(
            side_effect=[
                APITimeoutError(request=mock_request),
                APITimeoutError(request=mock_request),
                "success",
            ]
        )
        result = _call_with_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 3

    def test_call_with_retry_non_retryable_error(self) -> None:
        mock_func = MagicMock(side_effect=ValueError("bad value"))
        with pytest.raises(ValueError, match="bad value"):
            _call_with_retry(mock_func)
        assert mock_func.call_count == 1

    def test_call_with_retry_max_retries_exceeded(self) -> None:
        mock_request = MagicMock()
        mock_func = MagicMock(side_effect=APITimeoutError(request=mock_request))
        with pytest.raises(APITimeoutError):
            _call_with_retry(mock_func)
        assert mock_func.call_count == 3


class TestProfileExtractor:
    """Tests for ProfileExtractor."""

    @pytest.fixture
    def test_settings(self) -> Settings:
        return Settings(
            anthropic_api_key=SecretStr("sk-ant-test-key-12345"),
            max_tokens=4096,
        )

    @pytest.fixture
    def extractor(self, test_settings: Settings) -> ProfileExtractor:
        return ProfileExtractor(settings=test_settings)

    @pytest.fixture
    def mock_extraction_schema(self) -> ProfileExtractionSchema:
        return ProfileExtractionSchema(
            contact=ContactInfoSchema(
                full_name="John Doe",
                email="john.doe@example.com",
                phone="+1-555-1234",
                location="San Francisco, CA",
                linkedin_url="https://linkedin.com/in/johndoe",
                github_url="https://github.com/johndoe",
            ),
            professional_summary="Experienced software engineer with 6 years building scalable systems",
            headline="Senior Software Engineer",
            years_of_experience=6.0,
            experiences=[
                ExperienceSchema(
                    company="Acme Corp",
                    title="Senior Developer",
                    location="San Francisco, CA",
                    start_date="2021-01-01",
                    end_date=None,
                    is_current=True,
                    description="Leading microservices development",
                    achievements=[
                        "Built microservices handling 5M requests per day",
                        "Reduced API response time by 45%",
                    ],
                    technologies=["Python", "AWS", "Docker"],
                    metrics={"requests": "5M", "response_time_reduction": "45%"},
                )
            ],
            education=[
                EducationSchema(
                    institution="MIT",
                    degree="Bachelor of Science",
                    field_of_study="Computer Science",
                    location="Cambridge, MA",
                    start_date="2014-09-01",
                    graduation_date="2018-06-15",
                    gpa=3.7,
                    honors=["Dean's List"],
                    relevant_coursework=["Algorithms", "Systems"],
                )
            ],
            skills=[
                SkillSchema(
                    name="Python", category="programming", proficiency=5, years_experience=6.0
                ),
                SkillSchema(name="AWS", category="technical", proficiency=4, years_experience=5.0),
            ],
            languages=[["English", "Native"], ["Spanish", "Professional"]],
        )

    @pytest.fixture
    def mock_beta_response(self, mock_extraction_schema: ProfileExtractionSchema) -> MagicMock:
        mock_response = MagicMock(spec=ParsedBetaMessage)
        mock_response.id = "msg_test123"
        mock_response.type = "message"
        mock_response.role = "assistant"
        mock_response.content = [ParsedBetaTextBlock(type="text", text="extracted")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = BetaUsage(input_tokens=500, output_tokens=800)
        mock_response.parsed_output = mock_extraction_schema
        return mock_response

    def test_extract_empty_text_raises_error(self, extractor: ProfileExtractor) -> None:
        with pytest.raises(ExtractionError, match="Cannot extract profile from empty text"):
            extractor.extract("")

    def test_extract_whitespace_only_raises_error(self, extractor: ProfileExtractor) -> None:
        with pytest.raises(ExtractionError, match="Cannot extract profile from empty text"):
            extractor.extract("   \n\t  ")

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_success(
        self,
        mock_anthropic: MagicMock,
        extractor: ProfileExtractor,
        mock_beta_response: MagicMock,
        sample_raw_text: str,
    ) -> None:
        mock_client = MagicMock()
        mock_client.beta.messages.parse.return_value = mock_beta_response
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client
        profile = extractor.extract(sample_raw_text)

        assert isinstance(profile, PersonProfile)
        assert profile.contact.full_name == "John Doe"
        assert profile.contact.email == "john.doe@example.com"
        assert profile.years_of_experience == 6.0
        assert len(profile.experiences) == 1
        assert profile.experiences[0].company == "Acme Corp"
        assert len(profile.skills) == 2
        assert profile.raw_text is not None

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_api_refusal(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_client = MagicMock()
        refusal_response = MagicMock(spec=ParsedBetaMessage)
        refusal_response.stop_reason = "refusal"
        refusal_response.parsed_output = None
        mock_client.beta.messages.parse.return_value = refusal_response
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client

        with pytest.raises(ExtractionError, match="refused to process"):
            extractor.extract(sample_raw_text)

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_max_tokens_exceeded(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_client = MagicMock()
        truncated_response = MagicMock(spec=ParsedBetaMessage)
        truncated_response.stop_reason = "max_tokens"
        truncated_response.parsed_output = None
        mock_client.beta.messages.parse.return_value = truncated_response
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client

        with pytest.raises(ExtractionError, match="truncated due to max_tokens"):
            extractor.extract(sample_raw_text)

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_no_parsed_output(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_client = MagicMock()
        no_output_response = MagicMock(spec=ParsedBetaMessage)
        no_output_response.stop_reason = "end_turn"
        no_output_response.parsed_output = None
        mock_client.beta.messages.parse.return_value = no_output_response
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client

        with pytest.raises(ExtractionError, match="No parsed output"):
            extractor.extract(sample_raw_text)

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_api_timeout_retry_success(
        self,
        mock_anthropic: MagicMock,
        extractor: ProfileExtractor,
        mock_beta_response: MagicMock,
        sample_raw_text: str,
    ) -> None:
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.beta.messages.parse.side_effect = [
            APITimeoutError(request=mock_request),
            mock_beta_response,
        ]
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client
        profile = extractor.extract(sample_raw_text)

        assert isinstance(profile, PersonProfile)
        assert mock_client.beta.messages.parse.call_count == 2

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_api_connection_error_retry_exhausted(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_client.beta.messages.parse.side_effect = APIConnectionError(
            message="connection failed", request=mock_request
        )
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client

        with pytest.raises(ExtractionError, match="API call failed"):
            extractor.extract(sample_raw_text)
        assert mock_client.beta.messages.parse.call_count == 3

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_rate_limit_error(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_client.beta.messages.parse.side_effect = RateLimitError(
            "rate limited", response=mock_response, body=None
        )
        mock_anthropic.return_value = mock_client

        extractor._client = mock_client

        with pytest.raises(ExtractionError, match="API call failed"):
            extractor.extract(sample_raw_text)
        assert mock_client.beta.messages.parse.call_count == 3

    def test_parse_date_valid_iso(self, extractor: ProfileExtractor) -> None:
        parsed = extractor._parse_date("2023-06-15")
        assert parsed == date(2023, 6, 15)

    def test_parse_date_year_only(self, extractor: ProfileExtractor) -> None:
        parsed = extractor._parse_date("2023")
        assert parsed == date(2023, 1, 1)

    def test_parse_date_invalid(self, extractor: ProfileExtractor) -> None:
        parsed = extractor._parse_date("invalid-date")
        assert parsed is None

    def test_parse_date_none(self, extractor: ProfileExtractor) -> None:
        parsed = extractor._parse_date(None)
        assert parsed is None

    def test_parse_skill_category_valid(self, extractor: ProfileExtractor) -> None:
        assert extractor._parse_skill_category("programming") == SkillCategory.PROGRAMMING
        assert extractor._parse_skill_category("technical") == SkillCategory.TECHNICAL

    def test_parse_skill_category_case_insensitive(self, extractor: ProfileExtractor) -> None:
        assert extractor._parse_skill_category("PROGRAMMING") == SkillCategory.PROGRAMMING
        assert extractor._parse_skill_category("  Technical  ") == SkillCategory.TECHNICAL

    def test_parse_skill_category_invalid_defaults_to_other(
        self, extractor: ProfileExtractor
    ) -> None:
        assert extractor._parse_skill_category("unknown") == SkillCategory.OTHER
        assert extractor._parse_skill_category("invalid") == SkillCategory.OTHER

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_convert_to_profile_with_minimal_data(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor
    ) -> None:
        minimal_schema = ProfileExtractionSchema(
            contact=ContactInfoSchema(
                full_name="Jane Smith",
                email="jane@example.com",
            ),
        )

        profile = extractor._convert_to_profile(minimal_schema, "raw text")

        assert profile.contact.full_name == "Jane Smith"
        assert profile.contact.email == "jane@example.com"
        assert profile.experiences == []
        assert profile.skills == []
        assert profile.raw_text == "raw text"

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_convert_to_profile_skips_invalid_experience(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor
    ) -> None:
        schema = ProfileExtractionSchema(
            contact=ContactInfoSchema(full_name="Test", email="test@example.com"),
            experiences=[
                ExperienceSchema(company="Corp1", title="Engineer", start_date="2020-01-01"),
                ExperienceSchema(company="Corp2", title="Dev", start_date="invalid-date"),
                ExperienceSchema(company="Corp3", title="Lead", start_date="2022-01-01"),
            ],
        )

        profile = extractor._convert_to_profile(schema, "raw")

        assert len(profile.experiences) == 2
        assert profile.experiences[0].company == "Corp1"
        assert profile.experiences[1].company == "Corp3"

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_convert_to_profile_handles_languages(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor
    ) -> None:
        schema = ProfileExtractionSchema(
            contact=ContactInfoSchema(full_name="Test", email="test@example.com"),
            languages=[["English", "Native"], ["Spanish", "Professional"], ["French"]],
        )

        profile = extractor._convert_to_profile(schema, "raw")

        assert len(profile.languages) == 3
        assert profile.languages[0] == ("English", "Native")
        assert profile.languages[1] == ("Spanish", "Professional")
        assert profile.languages[2] == ("French", "")

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_convert_to_profile_validation_error(
        self, mock_anthropic: MagicMock, extractor: ProfileExtractor
    ) -> None:
        invalid_schema = ProfileExtractionSchema(
            contact=ContactInfoSchema(
                full_name="",
                email="invalid-email",
            ),
        )

        with pytest.raises(ExtractionError, match="validation failed"):
            extractor._convert_to_profile(invalid_schema, "raw")

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_extract_preserves_all_fields(
        self,
        mock_anthropic: MagicMock,
        extractor: ProfileExtractor,
        sample_raw_text: str,
    ) -> None:
        mock_client = MagicMock()
        complete_schema = ProfileExtractionSchema(
            contact=ContactInfoSchema(
                full_name="Alice Developer",
                email="alice@example.com",
                phone="+1-555-9999",
                location="Seattle, WA",
                linkedin_url="https://linkedin.com/in/alice",
                github_url="https://github.com/alice",
                portfolio_url="https://alice.dev",
            ),
            professional_summary="Full-stack developer with 8 years experience",
            headline="Senior Full-Stack Engineer",
            years_of_experience=8.0,
            skills=[
                SkillSchema(
                    name="Python",
                    category="programming",
                    proficiency=5,
                    years_experience=8.0,
                    keywords=["python3", "django", "flask"],
                )
            ],
            publications=["Paper on Distributed Systems"],
            awards=["Employee of the Year 2023"],
            volunteer_experience=["Tech mentor at Code.org"],
            interests=["Open source", "Machine learning"],
        )
        response = MagicMock(spec=ParsedBetaMessage)
        response.stop_reason = "end_turn"
        response.parsed_output = complete_schema
        mock_client.beta.messages.parse.return_value = response
        mock_anthropic.return_value = mock_client
        extractor._client = mock_client

        profile = extractor.extract(sample_raw_text)

        assert profile.contact.full_name == "Alice Developer"
        assert str(profile.contact.portfolio_url) == "https://alice.dev/"
        assert profile.professional_summary == "Full-stack developer with 8 years experience"
        assert profile.headline == "Senior Full-Stack Engineer"
        assert profile.years_of_experience == 8.0
        assert len(profile.skills) == 1
        assert profile.skills[0].keywords == ["python3", "django", "flask"]
        assert profile.publications == ["Paper on Distributed Systems"]
        assert profile.awards == ["Employee of the Year 2023"]
        assert profile.volunteer_experience == ["Tech mentor at Code.org"]
        assert profile.interests == ["Open source", "Machine learning"]

    @patch("resume_generator.extraction.profile.Anthropic")
    def test_call_claude_structured_uses_correct_parameters(
        self,
        mock_anthropic: MagicMock,
        extractor: ProfileExtractor,
        mock_beta_response: MagicMock,
        test_settings: Settings,
    ) -> None:
        mock_client = MagicMock()
        mock_client.beta.messages.parse.return_value = mock_beta_response
        mock_anthropic.return_value = mock_client
        extractor._client = mock_client

        extractor._call_claude_structured("test text")

        call_args = mock_client.beta.messages.parse.call_args
        assert call_args.kwargs["model"] == test_settings.claude_model.value
        assert call_args.kwargs["max_tokens"] == test_settings.max_tokens
        assert call_args.kwargs["betas"] == ["structured-outputs-2025-11-13"]
        assert call_args.kwargs["output_format"] == ProfileExtractionSchema
        assert len(call_args.kwargs["messages"]) == 1
        assert call_args.kwargs["messages"][0]["role"] == "user"
        assert "test text" in call_args.kwargs["messages"][0]["content"]

"""Unit tests for extraction module."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from resume_generator.claude_client import (
    ClaudeCLIError,
    ClaudeCLINotFoundError,
    ClaudeCLITimeoutError,
    InvokeResult,
)
from resume_generator.config import Settings
from resume_generator.extraction.profile import (
    ContactInfoSchema,
    EducationSchema,
    ExperienceSchema,
    ExtractionError,
    ProfileExtractionSchema,
    ProfileExtractor,
    SkillSchema,
)
from resume_generator.models.profile import (
    PersonProfile,
    SkillCategory,
)


class TestProfileExtractor:
    """Tests for ProfileExtractor."""

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

    def test_extract_empty_text_raises_error(self, extractor: ProfileExtractor) -> None:
        with pytest.raises(ExtractionError, match="Cannot extract profile from empty text"):
            extractor.extract("")

    def test_extract_whitespace_only_raises_error(self, extractor: ProfileExtractor) -> None:
        with pytest.raises(ExtractionError, match="Cannot extract profile from empty text"):
            extractor.extract("   \n\t  ")

    def test_extract_success(
        self,
        extractor: ProfileExtractor,
        mock_extraction_schema: ProfileExtractionSchema,
        sample_raw_text: str,
    ) -> None:
        mock_cli = MagicMock()
        json_response = mock_extraction_schema.model_dump_json()
        mock_cli.invoke.return_value = InvokeResult(
            success=True, output=json_response, exit_code=0
        )
        extractor._cli = mock_cli

        profile = extractor.extract(sample_raw_text)

        assert isinstance(profile, PersonProfile)
        assert profile.contact.full_name == "John Doe"
        assert profile.contact.email == "john.doe@example.com"
        assert profile.years_of_experience == 6.0
        assert len(profile.experiences) == 1
        assert profile.experiences[0].company == "Acme Corp"
        assert len(profile.skills) == 2
        assert profile.raw_text is not None

    def test_extract_cli_failure(
        self, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.return_value = InvokeResult(
            success=False, output="Error occurred", exit_code=1
        )
        extractor._cli = mock_cli

        with pytest.raises(ExtractionError, match="returned non-zero exit code"):
            extractor.extract(sample_raw_text)

    def test_extract_cli_error_exception(
        self, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.side_effect = ClaudeCLIError("CLI invocation failed")
        extractor._cli = mock_cli

        with pytest.raises(ExtractionError, match="Claude CLI error"):
            extractor.extract(sample_raw_text)

    def test_extract_timeout_error(
        self, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.side_effect = ClaudeCLITimeoutError("Timeout after 3600s")
        extractor._cli = mock_cli

        with pytest.raises(ExtractionError, match="Claude CLI error"):
            extractor.extract(sample_raw_text)

    def test_extract_not_found_error(
        self, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.side_effect = ClaudeCLINotFoundError("Claude CLI not found")
        extractor._cli = mock_cli

        with pytest.raises(ExtractionError, match="Claude CLI error"):
            extractor.extract(sample_raw_text)

    def test_extract_invalid_json_response(
        self, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.return_value = InvokeResult(
            success=True, output="This is not valid JSON", exit_code=0
        )
        extractor._cli = mock_cli

        with pytest.raises(ExtractionError, match="Failed to parse response"):
            extractor.extract(sample_raw_text)

    def test_extract_invalid_schema(
        self, extractor: ProfileExtractor, sample_raw_text: str
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.return_value = InvokeResult(
            success=True, output='{"invalid": "schema"}', exit_code=0
        )
        extractor._cli = mock_cli

        with pytest.raises(ExtractionError, match="Response validation failed"):
            extractor.extract(sample_raw_text)

    def test_extract_json_in_markdown_code_block(
        self,
        extractor: ProfileExtractor,
        mock_extraction_schema: ProfileExtractionSchema,
        sample_raw_text: str,
    ) -> None:
        mock_cli = MagicMock()
        json_content = mock_extraction_schema.model_dump_json()
        markdown_wrapped = f"```json\n{json_content}\n```"
        mock_cli.invoke.return_value = InvokeResult(
            success=True, output=markdown_wrapped, exit_code=0
        )
        extractor._cli = mock_cli

        profile = extractor.extract(sample_raw_text)

        assert isinstance(profile, PersonProfile)
        assert profile.contact.full_name == "John Doe"

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

    def test_convert_to_profile_with_minimal_data(
        self, extractor: ProfileExtractor
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

    def test_convert_to_profile_skips_invalid_experience(
        self, extractor: ProfileExtractor
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

    def test_convert_to_profile_handles_languages(
        self, extractor: ProfileExtractor
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

    def test_convert_to_profile_validation_error(
        self, extractor: ProfileExtractor
    ) -> None:
        invalid_schema = ProfileExtractionSchema(
            contact=ContactInfoSchema(
                full_name="",
                email="invalid-email",
            ),
        )

        with pytest.raises(ExtractionError, match="validation failed"):
            extractor._convert_to_profile(invalid_schema, "raw")

    def test_extract_preserves_all_fields(
        self,
        extractor: ProfileExtractor,
        sample_raw_text: str,
    ) -> None:
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

        mock_cli = MagicMock()
        mock_cli.invoke.return_value = InvokeResult(
            success=True, output=complete_schema.model_dump_json(), exit_code=0
        )
        extractor._cli = mock_cli

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

    def test_call_claude_uses_correct_parameters(
        self,
        extractor: ProfileExtractor,
        mock_extraction_schema: ProfileExtractionSchema,
        sample_raw_text: str,
    ) -> None:
        mock_cli = MagicMock()
        mock_cli.invoke.return_value = InvokeResult(
            success=True, output=mock_extraction_schema.model_dump_json(), exit_code=0
        )
        extractor._cli = mock_cli

        extractor.extract(sample_raw_text)

        mock_cli.invoke.assert_called_once()
        call_kwargs = mock_cli.invoke.call_args.kwargs
        assert "prompt" in call_kwargs
        assert "system" in call_kwargs
        assert sample_raw_text in call_kwargs["prompt"]

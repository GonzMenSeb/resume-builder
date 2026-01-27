"""Profile extraction using Claude to parse raw text into structured PersonProfile."""

import json
import logging
from datetime import date
from typing import Any

from anthropic import Anthropic
from pydantic import BaseModel, Field, ValidationError

from resume_generator.config import Settings, get_settings
from resume_generator.extraction.prompts import PROFILE_EXTRACTION_SYSTEM
from resume_generator.models.profile import (
    Certification,
    ContactInfo,
    Education,
    Experience,
    PersonProfile,
    Project,
    Skill,
    SkillCategory,
)

logger = logging.getLogger(__name__)

STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"


class ExtractionError(Exception):
    """Raised when profile extraction fails."""


class ContactInfoSchema(BaseModel):
    """Simplified schema for structured output extraction."""

    full_name: str = Field(description="Full legal name")
    email: str = Field(description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    location: str | None = Field(default=None, description="City and region/state")
    linkedin_url: str | None = Field(default=None, description="LinkedIn URL")
    github_url: str | None = Field(default=None, description="GitHub URL")
    portfolio_url: str | None = Field(default=None, description="Portfolio URL")


class SkillSchema(BaseModel):
    """Skill extraction schema."""

    name: str = Field(description="Skill name")
    category: str = Field(
        default="other",
        description="Category: technical, programming, frameworks, tools, languages, soft, domain, other",
    )
    proficiency: int | None = Field(default=None, description="Proficiency 1-5")
    years_experience: float | None = Field(default=None, description="Years of experience")
    keywords: list[str] = Field(default_factory=list, description="Related keywords")


class ExperienceSchema(BaseModel):
    """Work experience extraction schema."""

    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    location: str | None = Field(default=None, description="Job location")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="End date YYYY-MM-DD or null")
    is_current: bool = Field(default=False, description="Is current position")
    description: str | None = Field(default=None, description="Role description")
    achievements: list[str] = Field(default_factory=list, description="Achievement bullet points")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")
    metrics: dict[str, str] = Field(default_factory=dict, description="Quantified metrics")


class EducationSchema(BaseModel):
    """Education extraction schema."""

    institution: str = Field(description="Institution name")
    degree: str = Field(description="Degree type")
    field_of_study: str | None = Field(default=None, description="Major/field")
    location: str | None = Field(default=None, description="Location")
    start_date: str | None = Field(default=None, description="Start date")
    graduation_date: str | None = Field(default=None, description="Graduation date")
    gpa: float | None = Field(default=None, description="GPA if notable")
    honors: list[str] = Field(default_factory=list, description="Honors")
    relevant_coursework: list[str] = Field(default_factory=list, description="Relevant courses")


class CertificationSchema(BaseModel):
    """Certification extraction schema."""

    name: str = Field(description="Certification name")
    acronym: str | None = Field(default=None, description="Acronym")
    issuing_organization: str | None = Field(default=None, description="Issuer")
    date_earned: str | None = Field(default=None, description="Date earned")
    expiration_date: str | None = Field(default=None, description="Expiration date")
    credential_id: str | None = Field(default=None, description="Credential ID")


class ProjectSchema(BaseModel):
    """Project extraction schema."""

    name: str = Field(description="Project name")
    description: str | None = Field(default=None, description="Description")
    role: str | None = Field(default=None, description="Your role")
    url: str | None = Field(default=None, description="Project URL")
    repository_url: str | None = Field(default=None, description="Repository URL")
    start_date: str | None = Field(default=None, description="Start date")
    end_date: str | None = Field(default=None, description="End date")
    technologies: list[str] = Field(default_factory=list, description="Technologies")
    highlights: list[str] = Field(default_factory=list, description="Key achievements")


class ProfileExtractionSchema(BaseModel):
    """Top-level schema for Claude structured output extraction."""

    contact: ContactInfoSchema = Field(description="Contact information")
    professional_summary: str | None = Field(default=None, description="Professional summary")
    headline: str | None = Field(default=None, description="Professional headline")
    years_of_experience: float | None = Field(default=None, description="Total years experience")
    experiences: list[ExperienceSchema] = Field(default_factory=list, description="Work history")
    education: list[EducationSchema] = Field(default_factory=list, description="Education")
    skills: list[SkillSchema] = Field(default_factory=list, description="Skills")
    certifications: list[CertificationSchema] = Field(default_factory=list, description="Certs")
    projects: list[ProjectSchema] = Field(default_factory=list, description="Projects")
    publications: list[str] = Field(default_factory=list, description="Publications")
    awards: list[str] = Field(default_factory=list, description="Awards")
    languages: list[list[str]] = Field(default_factory=list, description="Languages as [name, proficiency]")
    volunteer_experience: list[str] = Field(default_factory=list, description="Volunteer work")
    interests: list[str] = Field(default_factory=list, description="Interests")


def _build_extraction_prompt(raw_text: str) -> str:
    """Build prompt for profile extraction."""
    return f"""Extract all professional information from the following text into structured JSON.

## Guidelines
- Extract only explicitly stated information; never fabricate data
- Use ISO date format YYYY-MM-DD; if only year known, use YYYY-01-01
- For skills, classify into appropriate categories
- Preserve original wording of achievements and descriptions
- Languages should be [language_name, proficiency_level] pairs

## Raw Text

<raw_text>
{raw_text}
</raw_text>

Extract all available information into the structured format."""


class ProfileExtractor:
    """Extracts structured PersonProfile from raw text using Claude's structured outputs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = Anthropic(api_key=self._settings.anthropic_api_key.get_secret_value())

    def extract(self, raw_text: str) -> PersonProfile:
        """Extract a PersonProfile from raw text using Claude's structured output mode.

        Uses Claude's JSON mode with constrained decoding to guarantee valid JSON
        output that matches the PersonProfile schema.

        Args:
            raw_text: Unstructured text containing person's professional info.

        Returns:
            Parsed and validated PersonProfile.

        Raises:
            ExtractionError: If extraction or parsing fails.
        """
        if not raw_text.strip():
            raise ExtractionError("Cannot extract profile from empty text")

        extracted = self._call_claude_structured(raw_text)
        profile = self._convert_to_profile(extracted, raw_text)
        return profile

    def _call_claude_structured(self, raw_text: str) -> ProfileExtractionSchema:
        """Call Claude API using structured output mode."""
        try:
            response = self._client.beta.messages.parse(
                model=self._settings.claude_model.value,
                max_tokens=self._settings.max_tokens,
                betas=[STRUCTURED_OUTPUTS_BETA],
                system=PROFILE_EXTRACTION_SYSTEM,
                messages=[{"role": "user", "content": _build_extraction_prompt(raw_text)}],
                output_format=ProfileExtractionSchema,
            )

            if response.stop_reason == "refusal":
                raise ExtractionError("Claude refused to process this request")

            if response.stop_reason == "max_tokens":
                raise ExtractionError("Response truncated due to max_tokens limit")

            if response.parsed_output is None:
                raise ExtractionError("No parsed output received from Claude")

            return response.parsed_output

        except ExtractionError:
            raise
        except Exception as e:
            logger.exception("Claude API call failed")
            raise ExtractionError(f"API call failed: {e}") from e

    def _convert_to_profile(
        self, extracted: ProfileExtractionSchema, raw_text: str
    ) -> PersonProfile:
        """Convert extraction schema to full PersonProfile with validated types."""
        try:
            contact = ContactInfo.model_validate(extracted.contact.model_dump())

            experiences = []
            for exp in extracted.experiences:
                start = self._parse_date(exp.start_date)
                if start is None:
                    logger.warning("Skipping experience with invalid start_date: %s", exp.company)
                    continue
                experiences.append(
                    Experience(
                        company=exp.company,
                        title=exp.title,
                        location=exp.location,
                        start_date=start,
                        end_date=self._parse_date(exp.end_date) if exp.end_date else None,
                        is_current=exp.is_current,
                        description=exp.description,
                        achievements=exp.achievements,
                        technologies=exp.technologies,
                        metrics=exp.metrics,
                    )
                )

            education = [
                Education(
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    location=edu.location,
                    start_date=self._parse_date(edu.start_date) if edu.start_date else None,
                    graduation_date=self._parse_date(edu.graduation_date)
                    if edu.graduation_date
                    else None,
                    gpa=edu.gpa,
                    honors=edu.honors,
                    relevant_coursework=edu.relevant_coursework,
                )
                for edu in extracted.education
            ]

            skills = [
                Skill(
                    name=sk.name,
                    category=self._parse_skill_category(sk.category),
                    proficiency=sk.proficiency,
                    years_experience=sk.years_experience,
                    keywords=sk.keywords,
                )
                for sk in extracted.skills
            ]

            certifications = [
                Certification(
                    name=cert.name,
                    acronym=cert.acronym,
                    issuing_organization=cert.issuing_organization,
                    date_earned=self._parse_date(cert.date_earned) if cert.date_earned else None,
                    expiration_date=self._parse_date(cert.expiration_date)
                    if cert.expiration_date
                    else None,
                    credential_id=cert.credential_id,
                )
                for cert in extracted.certifications
            ]

            projects = []
            for proj in extracted.projects:
                proj_data = proj.model_dump()
                proj_data["start_date"] = (
                    self._parse_date(proj.start_date) if proj.start_date else None
                )
                proj_data["end_date"] = self._parse_date(proj.end_date) if proj.end_date else None
                projects.append(Project.model_validate(proj_data))

            languages = [
                (lang[0], lang[1]) if len(lang) >= 2 else (lang[0], "")
                for lang in extracted.languages
                if lang
            ]

            return PersonProfile(
                contact=contact,
                professional_summary=extracted.professional_summary,
                headline=extracted.headline,
                years_of_experience=extracted.years_of_experience,
                experiences=experiences,
                education=education,
                skills=skills,
                certifications=certifications,
                projects=projects,
                publications=extracted.publications,
                awards=extracted.awards,
                languages=languages,
                volunteer_experience=extracted.volunteer_experience,
                interests=extracted.interests,
                raw_text=raw_text,
            )

        except ValidationError as e:
            logger.error("Profile validation failed: %s", e)
            raise ExtractionError(f"Profile validation failed: {e}") from e
        except Exception as e:
            logger.exception("Failed to convert extracted data to PersonProfile")
            raise ExtractionError(f"Conversion failed: {e}") from e

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        """Parse ISO date string to date object."""
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            if len(date_str) == 4 and date_str.isdigit():
                return date(int(date_str), 1, 1)
            logger.warning("Could not parse date: %s", date_str)
            return None

    @staticmethod
    def _parse_skill_category(category: str) -> SkillCategory:
        """Parse skill category string to enum."""
        category_lower = category.lower().strip()
        try:
            return SkillCategory(category_lower)
        except ValueError:
            return SkillCategory.OTHER


class LegacyProfileExtractor:
    """Legacy extractor using manual JSON parsing (fallback for older models)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = Anthropic(api_key=self._settings.anthropic_api_key.get_secret_value())

    def extract(self, raw_text: str) -> PersonProfile:
        """Extract using traditional JSON parsing."""
        if not raw_text.strip():
            raise ExtractionError("Cannot extract profile from empty text")

        from resume_generator.extraction.prompts import build_profile_extraction_prompt

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

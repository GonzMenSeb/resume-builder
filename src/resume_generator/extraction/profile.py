"""Profile extraction using Claude CLI to parse raw text into structured PersonProfile."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError

from resume_generator.claude_client import (
    ClaudeCLI,
    ClaudeCLIError,
    build_prompt_with_schema,
    parse_json_response,
)
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

if TYPE_CHECKING:
    from resume_generator.config import Settings

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when profile extraction fails."""


class ContactInfoSchema(BaseModel):
    """Schema for contact information extraction."""

    full_name: str = Field(description="Full legal name")
    email: str = Field(description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    location: str | None = Field(default=None, description="City and region/state")
    linkedin_url: str | None = Field(default=None, description="LinkedIn URL")
    github_url: str | None = Field(default=None, description="GitHub URL")
    portfolio_url: str | None = Field(default=None, description="Portfolio URL")


class SkillSchema(BaseModel):
    """Schema for skill extraction."""

    name: str = Field(description="Skill name")
    category: str = Field(
        default="other",
        description="Category: technical, programming, frameworks, tools, languages, soft, domain, other",
    )
    proficiency: int | None = Field(default=None, description="Proficiency 1-5")
    years_experience: float | None = Field(default=None, description="Years of experience")
    keywords: list[str] = Field(default_factory=list, description="Related keywords")


class ExperienceSchema(BaseModel):
    """Schema for work experience extraction."""

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
    """Schema for education extraction."""

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
    """Schema for certification extraction."""

    name: str = Field(description="Certification name")
    acronym: str | None = Field(default=None, description="Acronym")
    issuing_organization: str | None = Field(default=None, description="Issuer")
    date_earned: str | None = Field(default=None, description="Date earned")
    expiration_date: str | None = Field(default=None, description="Expiration date")
    credential_id: str | None = Field(default=None, description="Credential ID")


class ProjectSchema(BaseModel):
    """Schema for project extraction."""

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
    """Top-level schema for Claude profile extraction."""

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
    languages: list[list[str]] = Field(
        default_factory=list, description="Languages as [name, proficiency]"
    )
    volunteer_experience: list[str] = Field(default_factory=list, description="Volunteer work")
    interests: list[str] = Field(default_factory=list, description="Interests")


def _build_extraction_prompt(raw_text: str) -> str:
    """Build prompt for profile extraction with JSON schema."""
    base_prompt = f"""Extract all professional information from the following text into structured JSON.

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

    return build_prompt_with_schema(base_prompt, ProfileExtractionSchema)


class ProfileExtractor:
    """Extracts structured PersonProfile from raw text using Claude CLI."""

    def __init__(
        self,
        settings: Settings | None = None,
        claude_cli: ClaudeCLI | None = None,
    ) -> None:
        if claude_cli is not None:
            self._cli = claude_cli
        elif settings is not None:
            self._cli = ClaudeCLI(
                model=settings.claude_model.value,
                timeout=settings.claude_cli_timeout,
            )
        else:
            from resume_generator.config import get_settings

            s = get_settings()
            self._cli = ClaudeCLI(model=s.claude_model.value, timeout=s.claude_cli_timeout)

    def extract(self, raw_text: str) -> PersonProfile:
        """Extract a PersonProfile from raw text using Claude CLI.

        Args:
            raw_text: Unstructured text containing person's professional info.

        Returns:
            Parsed and validated PersonProfile.

        Raises:
            ExtractionError: If extraction or parsing fails.
        """
        if not raw_text.strip():
            raise ExtractionError("Cannot extract profile from empty text")

        extracted = self._call_claude(raw_text)
        return self._convert_to_profile(extracted, raw_text)

    def _call_claude(self, raw_text: str) -> ProfileExtractionSchema:
        """Call Claude CLI and parse response into extraction schema."""
        prompt = _build_extraction_prompt(raw_text)

        try:
            result = self._cli.invoke(prompt=prompt, system=PROFILE_EXTRACTION_SYSTEM)
        except ClaudeCLIError as e:
            logger.exception("Claude CLI invocation failed")
            raise ExtractionError(f"Claude CLI error: {e}") from e

        if result.failed:
            raise ExtractionError(f"Claude CLI returned non-zero exit code: {result.exit_code}")

        try:
            data = parse_json_response(result.output)
        except ValueError as e:
            logger.error("Failed to parse JSON from Claude response: %s", e)
            raise ExtractionError(f"Failed to parse response: {e}") from e

        try:
            return ProfileExtractionSchema.model_validate(data)
        except ValidationError as e:
            logger.error("Response validation failed: %s", e)
            raise ExtractionError(f"Response validation failed: {e}") from e

    def _convert_to_profile(
        self,
        extracted: ProfileExtractionSchema,
        raw_text: str,
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
                    graduation_date=(
                        self._parse_date(edu.graduation_date) if edu.graduation_date else None
                    ),
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
                    expiration_date=(
                        self._parse_date(cert.expiration_date) if cert.expiration_date else None
                    ),
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

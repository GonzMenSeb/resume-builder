"""Pydantic models for person profile data extracted from raw inputs."""

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator


class SkillCategory(str, Enum):
    """Categories for grouping skills."""

    TECHNICAL = "technical"
    PROGRAMMING = "programming"
    FRAMEWORKS = "frameworks"
    TOOLS = "tools"
    LANGUAGES = "languages"
    SOFT = "soft"
    DOMAIN = "domain"
    OTHER = "other"


class ContactInfo(BaseModel):
    """Contact information for the profile."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Annotated[str, Field(min_length=1, description="Full legal name")]
    email: EmailStr | None = Field(default=None, description="Professional email address")
    phone: str | None = Field(default=None, description="Phone number with country code")
    location: str | None = Field(
        default=None, description="City and region/state (full address not required)"
    )
    linkedin_url: HttpUrl | None = Field(default=None, description="LinkedIn profile URL")
    github_url: HttpUrl | None = Field(default=None, description="GitHub profile URL")
    portfolio_url: HttpUrl | None = Field(default=None, description="Personal website or portfolio")
    additional_urls: list[HttpUrl] = Field(
        default_factory=list, description="Other relevant profile URLs"
    )


class Skill(BaseModel):
    """A single skill with optional proficiency and category."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, description="Skill name")]
    category: SkillCategory = Field(default=SkillCategory.OTHER, description="Skill category")
    proficiency: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Proficiency level 1-5 (optional)",
    )
    years_experience: float | None = Field(
        default=None, ge=0, description="Years of experience with this skill"
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Related keywords/synonyms for ATS matching",
    )


class Experience(BaseModel):
    """Work experience entry."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: Annotated[str, Field(min_length=1, description="Company/organization name")]
    title: Annotated[str, Field(min_length=1, description="Job title")]
    location: str | None = Field(default=None, description="Job location")
    start_date: date = Field(description="Start date")
    end_date: date | None = Field(default=None, description="End date (None if current)")
    is_current: bool = Field(default=False, description="Whether this is the current position")
    description: str | None = Field(default=None, description="Role description/summary")
    achievements: list[str] = Field(
        default_factory=list,
        description="List of achievements/accomplishments (raw bullet points)",
    )
    technologies: list[str] = Field(
        default_factory=list, description="Technologies/tools used in this role"
    )
    metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Quantified metrics (e.g., {'revenue_increase': '33%'})",
    )

    @model_validator(mode="after")
    def infer_current(self) -> "Experience":
        if not self.is_current and self.end_date is None:
            self.is_current = True
        return self


class Education(BaseModel):
    """Education entry."""

    model_config = ConfigDict(str_strip_whitespace=True)

    institution: Annotated[str, Field(min_length=1, description="Institution name")]
    degree: str = Field(description="Degree type (e.g., 'Bachelor of Science')")
    field_of_study: str | None = Field(default=None, description="Major/field of study")
    location: str | None = Field(default=None, description="Institution location")
    start_date: date | None = Field(default=None, description="Start date")
    graduation_date: date | None = Field(default=None, description="Graduation date")
    gpa: float | None = Field(default=None, ge=0.0, le=4.0, description="GPA if notable")
    honors: list[str] = Field(default_factory=list, description="Honors and awards")
    relevant_coursework: list[str] = Field(
        default_factory=list, description="Relevant coursework (for recent graduates)"
    )
    activities: list[str] = Field(default_factory=list, description="Extracurricular activities")


class Certification(BaseModel):
    """Professional certification or license."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, description="Certification name")]
    acronym: str | None = Field(default=None, description="Common acronym (e.g., 'PMP', 'AWS-SAA')")
    issuing_organization: str | None = Field(default=None, description="Certifying body")
    date_earned: date | None = Field(default=None, description="Date certification was earned")
    expiration_date: date | None = Field(default=None, description="Expiration date if applicable")
    credential_id: str | None = Field(default=None, description="Credential ID for verification")
    url: HttpUrl | None = Field(default=None, description="Verification URL")


class Project(BaseModel):
    """Personal or professional project."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, description="Project name")]
    description: str | None = Field(default=None, description="Project description")
    role: str | None = Field(default=None, description="Your role in the project")
    url: HttpUrl | None = Field(default=None, description="Project URL")
    repository_url: HttpUrl | None = Field(default=None, description="Source code repository URL")
    start_date: date | None = Field(default=None, description="Project start date")
    end_date: date | None = Field(default=None, description="Project end date")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")
    highlights: list[str] = Field(default_factory=list, description="Key achievements/features")


class PersonProfile(BaseModel):
    """Complete profile of a person for resume generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    contact: ContactInfo = Field(description="Contact information")
    professional_summary: str | None = Field(
        default=None,
        description="Raw professional summary or bio (will be optimized)",
    )
    headline: str | None = Field(
        default=None,
        description="Professional headline/tagline",
    )
    years_of_experience: float | None = Field(
        default=None,
        ge=0,
        description="Total years of professional experience",
    )
    experiences: list[Experience] = Field(
        default_factory=list, description="Work experience entries"
    )
    education: list[Education] = Field(default_factory=list, description="Education entries")
    skills: list[Skill] = Field(default_factory=list, description="Skills")
    certifications: list[Certification] = Field(
        default_factory=list, description="Certifications and licenses"
    )
    projects: list[Project] = Field(default_factory=list, description="Notable projects")
    publications: list[str] = Field(default_factory=list, description="Publications and papers")
    awards: list[str] = Field(default_factory=list, description="Awards and recognitions")
    languages: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Spoken languages as (language, proficiency) tuples",
    )
    volunteer_experience: list[str] = Field(
        default_factory=list, description="Volunteer work descriptions"
    )
    interests: list[str] = Field(
        default_factory=list, description="Hobbies and interests (if relevant)"
    )
    raw_text: str | None = Field(
        default=None,
        description="Original raw text from which profile was extracted",
    )

    def get_skills_by_category(self, category: SkillCategory) -> list[Skill]:
        """Get skills filtered by category."""
        return [s for s in self.skills if s.category == category]

    def get_all_technologies(self) -> set[str]:
        """Aggregate all technologies from experiences and projects."""
        techs: set[str] = set()
        for exp in self.experiences:
            techs.update(exp.technologies)
        for proj in self.projects:
            techs.update(proj.technologies)
        return techs

    def get_current_position(self) -> Experience | None:
        """Get the current work position if any."""
        for exp in self.experiences:
            if exp.is_current:
                return exp
        return None

    def compute_years_of_experience(self) -> float:
        """Calculate total years of experience from work history."""
        if not self.experiences:
            return 0.0

        total_days = 0
        today = date.today()
        for exp in self.experiences:
            end = exp.end_date or today
            delta = (end - exp.start_date).days
            if delta > 0:
                total_days += delta

        return round(total_days / 365.25, 1)

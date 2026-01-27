"""Pydantic models for job description and requirements parsing."""

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, model_validator


class ExperienceLevel(str, Enum):
    """Seniority/experience level classifications."""

    INTERN = "intern"
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"


class EmploymentType(str, Enum):
    """Employment type classifications."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class WorkArrangement(str, Enum):
    """Work location/arrangement type."""

    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class RequirementPriority(str, Enum):
    """Priority level for job requirements."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice_to_have"


class JobRequirement(BaseModel):
    """A single job requirement extracted from a job posting."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: Annotated[str, Field(min_length=1, description="Requirement text as stated")]
    priority: RequirementPriority = Field(
        default=RequirementPriority.PREFERRED,
        description="Requirement priority level",
    )
    category: str | None = Field(
        default=None,
        description="Category (e.g., 'technical', 'education', 'soft_skill', 'experience')",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords extracted from this requirement for ATS matching",
    )
    years_experience: int | None = Field(
        default=None,
        ge=0,
        description="Years of experience required if specified",
    )


class SalaryRange(BaseModel):
    """Salary information for a job posting."""

    model_config = ConfigDict(str_strip_whitespace=True)

    min_salary: float | None = Field(default=None, ge=0, description="Minimum salary")
    max_salary: float | None = Field(default=None, ge=0, description="Maximum salary")
    currency: str = Field(default="USD", description="Currency code")
    period: str = Field(default="yearly", description="Pay period (yearly, monthly, hourly)")

    @computed_field
    @property
    def display_text(self) -> str:
        if self.min_salary and self.max_salary:
            return (
                f"{self.currency} {self.min_salary:,.0f} - {self.max_salary:,.0f} ({self.period})"
            )
        if self.min_salary:
            return f"{self.currency} {self.min_salary:,.0f}+ ({self.period})"
        if self.max_salary:
            return f"Up to {self.currency} {self.max_salary:,.0f} ({self.period})"
        return "Not specified"


class JobDescription(BaseModel):
    """Complete parsed job description for resume tailoring."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Annotated[str, Field(min_length=1, description="Job title")]
    company: str | None = Field(default=None, description="Company name")
    location: str | None = Field(default=None, description="Job location")
    work_arrangement: WorkArrangement | None = Field(
        default=None, description="Remote/onsite/hybrid"
    )
    employment_type: EmploymentType = Field(
        default=EmploymentType.FULL_TIME, description="Employment type"
    )
    experience_level: ExperienceLevel | None = Field(
        default=None, description="Required experience level"
    )
    department: str | None = Field(default=None, description="Department or team")

    description: str | None = Field(default=None, description="Full job description text")
    responsibilities: list[str] = Field(default_factory=list, description="Key responsibilities")
    requirements: list[JobRequirement] = Field(default_factory=list, description="Job requirements")
    benefits: list[str] = Field(default_factory=list, description="Benefits offered")

    salary: SalaryRange | None = Field(default=None, description="Salary information")
    posting_url: HttpUrl | None = Field(default=None, description="Original job posting URL")
    posted_date: date | None = Field(default=None, description="Date job was posted")
    application_deadline: date | None = Field(default=None, description="Application deadline")

    required_skills: list[str] = Field(default_factory=list, description="Hard skills required")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    required_education: str | None = Field(default=None, description="Education requirement")
    required_certifications: list[str] = Field(
        default_factory=list, description="Required certifications"
    )

    min_years_experience: int | None = Field(
        default=None, ge=0, description="Minimum years of experience"
    )
    max_years_experience: int | None = Field(
        default=None, ge=0, description="Maximum years (for range)"
    )

    raw_text: str | None = Field(default=None, description="Original raw text of the job posting")

    @model_validator(mode="after")
    def validate_experience_range(self) -> "JobDescription":
        if (
            self.min_years_experience
            and self.max_years_experience
            and self.min_years_experience > self.max_years_experience
        ):
            self.min_years_experience, self.max_years_experience = (
                self.max_years_experience,
                self.min_years_experience,
            )
        return self

    @computed_field
    @property
    def all_keywords(self) -> list[str]:
        """Aggregate all keywords for ATS matching."""
        keywords: set[str] = set()
        keywords.update(self.required_skills)
        keywords.update(self.preferred_skills)
        keywords.update(self.required_certifications)
        for req in self.requirements:
            keywords.update(req.keywords)
        return sorted(keywords)

    @computed_field
    @property
    def required_requirements(self) -> list[JobRequirement]:
        return [r for r in self.requirements if r.priority == RequirementPriority.REQUIRED]

    @computed_field
    @property
    def preferred_requirements(self) -> list[JobRequirement]:
        return [r for r in self.requirements if r.priority == RequirementPriority.PREFERRED]

    def get_keyword_set(self) -> set[str]:
        """Get deduplicated set of all keywords (lowercase) for matching."""
        return {kw.lower() for kw in self.all_keywords}

    def calculate_match_score(self, candidate_keywords: set[str]) -> float:
        """
        Calculate keyword match score between job and candidate.
        Returns a float between 0 and 1.
        """
        job_keywords = self.get_keyword_set()
        if not job_keywords:
            return 0.0
        candidate_lower = {kw.lower() for kw in candidate_keywords}
        matches = job_keywords & candidate_lower
        return len(matches) / len(job_keywords)

    def get_experience_range_str(self) -> str:
        """Get formatted experience range string."""
        if self.min_years_experience and self.max_years_experience:
            return f"{self.min_years_experience}-{self.max_years_experience} years"
        if self.min_years_experience:
            return f"{self.min_years_experience}+ years"
        if self.max_years_experience:
            return f"Up to {self.max_years_experience} years"
        return "Not specified"

"""Pydantic models for optimized resume structure ready for rendering."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, computed_field, model_validator


class BulletType(str, Enum):
    """Type of bullet point based on content structure."""

    XYZ = "xyz"  # Accomplished [X] as measured by [Y], by doing [Z]
    ACTION_RESULT = "action_result"  # Action verb + quantified result
    SKILL_BASED = "skill_based"  # Demonstrates specific skill/competency
    GENERIC = "generic"  # Standard descriptive bullet


class SectionType(str, Enum):
    """Standard resume section types for ATS recognition."""

    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"
    PROJECTS = "projects"
    PUBLICATIONS = "publications"
    AWARDS = "awards"
    LANGUAGES = "languages"
    VOLUNTEER = "volunteer"
    CUSTOM = "custom"


class ResumeBullet(BaseModel):
    """Optimized resume bullet point following research best practices."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: Annotated[str, Field(min_length=10, description="Bullet point text")]
    bullet_type: BulletType = Field(
        default=BulletType.GENERIC, description="Classification of bullet structure"
    )
    action_verb: str | None = Field(
        default=None, description="Leading action verb (e.g., 'Engineered', 'Optimized')"
    )
    metrics: dict[str, str] = Field(
        default_factory=dict,
        description="Quantified metrics extracted from bullet (e.g., {'improvement': '40%'})",
    )
    keywords: list[str] = Field(default_factory=list, description="ATS keywords present in bullet")
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance to target job (0-1), used for ordering",
    )
    original_text: str | None = Field(default=None, description="Original text before optimization")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_metrics(self) -> bool:
        return bool(self.metrics)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def word_count(self) -> int:
        return len(self.text.split())


class ResumeExperience(BaseModel):
    """Optimized work experience entry for resume rendering."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: Annotated[str, Field(min_length=1, description="Company name")]
    title: Annotated[str, Field(min_length=1, description="Job title")]
    location: str | None = Field(default=None, description="Location (City, State/Country)")
    start_date: date = Field(description="Position start date")
    end_date: date | None = Field(default=None, description="Position end date")
    is_current: bool = Field(default=False, description="Current position flag")
    bullets: list[ResumeBullet] = Field(
        default_factory=list,
        min_length=2,
        max_length=7,
        description="3-5 optimized bullet points per research guidelines",
    )
    technologies: list[str] = Field(
        default_factory=list, description="Key technologies (for skills-based filtering)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def date_range_str(self) -> str:
        start = self.start_date.strftime("%b %Y")
        end = (
            "Present"
            if self.is_current or self.end_date is None
            else self.end_date.strftime("%b %Y")
        )
        return f"{start} - {end}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_months(self) -> int:
        end = self.end_date or date.today()
        return (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)

    @model_validator(mode="after")
    def sort_bullets_by_relevance(self) -> ResumeExperience:
        self.bullets = sorted(self.bullets, key=lambda b: b.relevance_score, reverse=True)
        return self


class ResumeEducation(BaseModel):
    """Education entry formatted for resume."""

    model_config = ConfigDict(str_strip_whitespace=True)

    institution: Annotated[str, Field(min_length=1, description="Institution name")]
    degree: str = Field(description="Degree (e.g., 'B.S. in Computer Science')")
    location: str | None = Field(default=None, description="Institution location")
    graduation_date: date | None = Field(default=None, description="Graduation date")
    gpa: str | None = Field(default=None, description="GPA if notable (formatted string)")
    honors: list[str] = Field(default_factory=list, description="Honors and distinctions")
    relevant_coursework: list[str] = Field(
        default_factory=list, description="Relevant courses (for recent grads)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def graduation_str(self) -> str | None:
        if not self.graduation_date:
            return None
        return self.graduation_date.strftime("%b %Y")


class ResumeCertification(BaseModel):
    """Certification formatted for resume."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, description="Certification name")]
    issuer: str | None = Field(default=None, description="Issuing organization")
    date_earned: date | None = Field(default=None, description="Date earned")
    credential_id: str | None = Field(default=None, description="Credential ID")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_text(self) -> str:
        parts = [self.name]
        if self.issuer:
            parts.append(f"({self.issuer})")
        if self.date_earned:
            parts.append(f"- {self.date_earned.strftime('%Y')}")
        return " ".join(parts)


class ResumeProject(BaseModel):
    """Project entry formatted for resume."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, description="Project name")]
    url: HttpUrl | None = Field(default=None, description="Project URL")
    description: str | None = Field(default=None, description="Brief description")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")
    highlights: list[str] = Field(default_factory=list, description="Key achievements")


class ResumeSkillGroup(BaseModel):
    """Grouped skills for resume display."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: str = Field(description="Category name (e.g., 'Languages', 'Frameworks')")
    skills: list[str] = Field(min_length=1, description="Skills in this category")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_text(self) -> str:
        return f"{self.category}: {', '.join(self.skills)}"


class ResumeSection(BaseModel):
    """Generic resume section container."""

    model_config = ConfigDict(str_strip_whitespace=True)

    section_type: SectionType = Field(description="Section type for ATS recognition")
    title: str = Field(description="Section title as displayed")
    content: (
        str
        | list[ResumeExperience]
        | list[ResumeEducation]
        | list[ResumeCertification]
        | list[ResumeProject]
        | list[ResumeSkillGroup]
        | list[str]
    ) = Field(description="Section content (type depends on section_type)")
    visible: bool = Field(default=True, description="Whether to render this section")
    order: int = Field(default=0, ge=0, description="Display order (lower = higher)")


class ResumeContact(BaseModel):
    """Contact information formatted for resume header."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, description="Full name")]
    email: str = Field(description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    location: str | None = Field(default=None, description="Location (City, State)")
    linkedin_url: HttpUrl | None = Field(default=None, description="LinkedIn URL")
    github_url: HttpUrl | None = Field(default=None, description="GitHub URL")
    portfolio_url: HttpUrl | None = Field(default=None, description="Portfolio URL")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def links(self) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        if self.linkedin_url:
            result.append(("LinkedIn", str(self.linkedin_url)))
        if self.github_url:
            result.append(("GitHub", str(self.github_url)))
        if self.portfolio_url:
            result.append(("Portfolio", str(self.portfolio_url)))
        return result


class ResumeDocument(BaseModel):
    """Complete resume document ready for rendering/generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    contact: ResumeContact = Field(description="Header contact information")
    professional_summary: str | None = Field(
        default=None,
        description="Professional summary (50-100 words per research guidelines)",
    )
    headline: str | None = Field(default=None, description="Professional headline/tagline")
    experiences: list[ResumeExperience] = Field(
        default_factory=list, description="Work experience entries"
    )
    education: list[ResumeEducation] = Field(default_factory=list, description="Education entries")
    skills: list[ResumeSkillGroup] = Field(default_factory=list, description="Grouped skills")
    certifications: list[ResumeCertification] = Field(
        default_factory=list, description="Certifications"
    )
    projects: list[ResumeProject] = Field(default_factory=list, description="Notable projects")
    additional_sections: list[ResumeSection] = Field(
        default_factory=list, description="Custom sections (awards, publications, etc.)"
    )
    target_job_title: str | None = Field(
        default=None, description="Job title this resume is tailored for"
    )
    keyword_match_rate: float | None = Field(
        default=None, ge=0.0, le=1.0, description="ATS keyword match rate if computed"
    )
    optimization_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Overall optimization score"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_bullet_count(self) -> int:
        return sum(len(exp.bullets) for exp in self.experiences)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_quantified_achievements(self) -> bool:
        return any(b.has_metrics for exp in self.experiences for b in exp.bullets)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary_word_count(self) -> int:
        if not self.professional_summary:
            return 0
        return len(self.professional_summary.split())

    def get_all_keywords(self) -> set[str]:
        """Extract all keywords from the resume for ATS analysis."""
        keywords: set[str] = set()
        for exp in self.experiences:
            keywords.update(exp.technologies)
            for bullet in exp.bullets:
                keywords.update(bullet.keywords)
        for skill_group in self.skills:
            keywords.update(skill_group.skills)
        return keywords

    def get_sections_ordered(self) -> list[ResumeSection]:
        """Get all sections in display order."""
        sections: list[ResumeSection] = []

        if self.professional_summary:
            sections.append(
                ResumeSection(
                    section_type=SectionType.SUMMARY,
                    title="Professional Summary",
                    content=self.professional_summary,
                    order=0,
                )
            )

        if self.experiences:
            sections.append(
                ResumeSection(
                    section_type=SectionType.EXPERIENCE,
                    title="Experience",
                    content=self.experiences,
                    order=1,
                )
            )

        if self.education:
            sections.append(
                ResumeSection(
                    section_type=SectionType.EDUCATION,
                    title="Education",
                    content=self.education,
                    order=2,
                )
            )

        if self.skills:
            sections.append(
                ResumeSection(
                    section_type=SectionType.SKILLS,
                    title="Skills",
                    content=self.skills,
                    order=3,
                )
            )

        if self.certifications:
            sections.append(
                ResumeSection(
                    section_type=SectionType.CERTIFICATIONS,
                    title="Certifications",
                    content=self.certifications,
                    order=4,
                )
            )

        if self.projects:
            sections.append(
                ResumeSection(
                    section_type=SectionType.PROJECTS,
                    title="Projects",
                    content=self.projects,
                    order=5,
                )
            )

        sections.extend(self.additional_sections)
        return sorted(sections, key=lambda s: s.order)

    def compact(self, min_bullets_per_job: int = 2) -> ResumeDocument:
        """Create a compacted copy with reduced bullets to fit page constraints."""
        compacted_experiences = []
        for exp in self.experiences:
            if len(exp.bullets) > min_bullets_per_job:
                reduced_bullets = exp.bullets[:max(min_bullets_per_job, len(exp.bullets) - 1)]
                compacted_exp = exp.model_copy(update={"bullets": reduced_bullets})
                compacted_experiences.append(compacted_exp)
            else:
                compacted_experiences.append(exp)

        return self.model_copy(update={"experiences": compacted_experiences})

"""Resume optimizer using Claude CLI to transform PersonProfile into optimized ResumeDocument."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, Field, ValidationError

from resume_generator.claude_client import (
    ClaudeCLI,
    ClaudeCLIError,
    build_prompt_with_schema,
    parse_json_response,
)
from resume_generator.models.profile import PersonProfile
from resume_generator.models.resume import (
    BulletType,
    ResumeBullet,
    ResumeCertification,
    ResumeContact,
    ResumeDocument,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeSkillGroup,
)
from resume_generator.optimization.prompts import (
    RESUME_OPTIMIZER_SYSTEM,
    build_bullet_batch_prompt,
    build_professional_summary_prompt,
    build_skills_optimization_prompt,
)

if TYPE_CHECKING:
    from resume_generator.config import Settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class OptimizationError(Exception):
    """Raised when resume optimization fails."""


class OptimizedBulletSchema(BaseModel):
    text: str = Field(description="Optimized bullet text")
    action_verb: str = Field(description="Leading action verb")
    bullet_type: str = Field(
        default="generic", description="Type: xyz, action_result, skill_based, generic"
    )
    has_metrics: bool = Field(default=False, description="Contains quantified metrics")
    metrics: dict[str, str] = Field(default_factory=dict, description="Extracted metrics")
    keywords: list[str] = Field(default_factory=list, description="ATS keywords")
    relevance_score: float = Field(default=0.5, description="Relevance score 0-1")
    original_index: int = Field(default=0, description="Original position")


class BulletBatchResultSchema(BaseModel):
    bullets: list[OptimizedBulletSchema] = Field(description="Optimized bullets")
    removed_bullets: list[dict[str, Any]] = Field(
        default_factory=list, description="Removed bullets with reasons"
    )
    overall_quality_score: float = Field(default=0.5, description="Quality score 0-1")


class ProfessionalSummarySchema(BaseModel):
    summary: str = Field(description="Professional summary text")
    word_count: int = Field(description="Word count")
    keywords_included: list[str] = Field(default_factory=list, description="Keywords in summary")
    tailored_for_job: bool = Field(default=False, description="Whether tailored for specific job")


class SkillGroupSchema(BaseModel):
    category: str = Field(description="Category name")
    skills: list[str] = Field(description="Skills in this category")
    priority: int = Field(default=0, description="Display priority")


class SkillsOptimizationSchema(BaseModel):
    skill_groups: list[SkillGroupSchema] = Field(description="Organized skill groups")
    added_skills: list[str] = Field(
        default_factory=list, description="Skills added from experience"
    )
    removed_skills: list[dict[str, str]] = Field(
        default_factory=list, description="Removed skills with reasons"
    )
    total_skills_count: int = Field(default=0, description="Total number of skills")


class ResumeOptimizer:
    """Transforms PersonProfile into optimized ResumeDocument using Claude CLI."""

    def __init__(
        self,
        settings: Settings | None = None,
        claude_cli: ClaudeCLI | None = None,
    ) -> None:
        if claude_cli is not None:
            self._cli = claude_cli
            self._settings = settings
        elif settings is not None:
            self._cli = ClaudeCLI(
                model=settings.claude_model.value,
                timeout=settings.claude_cli_timeout,
            )
            self._settings = settings
        else:
            from resume_generator.config import get_settings

            s = get_settings()
            self._cli = ClaudeCLI(model=s.claude_model.value, timeout=s.claude_cli_timeout)
            self._settings = s

    def optimize(
        self,
        profile: PersonProfile,
        target_job_title: str | None = None,
        target_keywords: list[str] | None = None,
    ) -> ResumeDocument:
        """Transform a PersonProfile into an optimized ResumeDocument.

        Args:
            profile: The extracted person profile to optimize.
            target_job_title: Optional job title to tailor resume for.
            target_keywords: Optional keywords to incorporate for ATS optimization.

        Returns:
            Optimized ResumeDocument ready for rendering.

        Raises:
            OptimizationError: If optimization fails.
        """
        contact = self._build_contact(profile)
        optimized_experiences = self._optimize_experiences(profile, target_keywords)
        professional_summary = self._generate_summary(profile, target_job_title, target_keywords)
        skills = self._optimize_skills(profile, target_keywords)
        education = self._build_education(profile)
        certifications = self._build_certifications(profile)
        projects = self._build_projects(profile)

        quality_scores = [
            exp.bullets[0].relevance_score for exp in optimized_experiences if exp.bullets
        ]
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5

        return ResumeDocument(
            contact=contact,
            professional_summary=professional_summary,
            headline=profile.headline,
            experiences=optimized_experiences,
            education=education,
            skills=skills,
            certifications=certifications,
            projects=projects,
            target_job_title=target_job_title,
            optimization_score=avg_score,
        )

    def _build_contact(self, profile: PersonProfile) -> ResumeContact:
        return ResumeContact(
            name=profile.contact.full_name,
            email=profile.contact.email,
            phone=profile.contact.phone,
            location=profile.contact.location,
            linkedin_url=profile.contact.linkedin_url,
            github_url=profile.contact.github_url,
            portfolio_url=profile.contact.portfolio_url,
        )

    def _optimize_experiences(
        self,
        profile: PersonProfile,
        target_keywords: list[str] | None,
    ) -> list[ResumeExperience]:
        max_bullets = self._settings.max_bullets_per_job if self._settings else 5

        optimized: list[ResumeExperience] = []
        for exp in profile.experiences:
            if not exp.achievements:
                main_text = exp.description or f"Worked as {exp.title} at {exp.company}"
                bullets = [
                    ResumeBullet(
                        text=main_text,
                        bullet_type=BulletType.GENERIC,
                        relevance_score=0.3,
                    ),
                    ResumeBullet(
                        text=f"Contributed to {exp.company} projects as {exp.title}",
                        bullet_type=BulletType.GENERIC,
                        relevance_score=0.3,
                    ),
                ]
            else:
                bullets = self._optimize_bullets(
                    achievements=exp.achievements,
                    role_title=exp.title,
                    company=exp.company,
                    target_keywords=target_keywords,
                    max_bullets=max_bullets,
                )

            if len(bullets) < 2:
                logger.warning(
                    "Skipping experience '%s' at '%s' - insufficient bullets (%d < 2)",
                    exp.title,
                    exp.company,
                    len(bullets),
                )
                continue

            optimized.append(
                ResumeExperience(
                    company=exp.company,
                    title=exp.title,
                    location=exp.location,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    bullets=bullets,
                    technologies=exp.technologies,
                )
            )
        return optimized

    def _optimize_bullets(
        self,
        achievements: list[str],
        role_title: str,
        company: str,
        target_keywords: list[str] | None,
        max_bullets: int,
    ) -> list[ResumeBullet]:
        min_bullets = self._settings.min_bullets_per_job if self._settings else 2
        language = self._settings.output_language.value if self._settings else None
        max_words = self._settings.max_bullet_words if self._settings else None
        prompt = build_bullet_batch_prompt(
            achievements=achievements,
            role_title=role_title,
            company=company,
            target_keywords=target_keywords,
            language=language,
            max_words=max_words,
        )

        try:
            result = self._call_claude_structured(prompt, BulletBatchResultSchema)
        except OptimizationError as e:
            logger.warning("Bullet optimization failed, using original: %s", e)
            return [
                ResumeBullet(text=a, bullet_type=BulletType.GENERIC, relevance_score=0.5)
                for a in achievements[:max_bullets]
            ]

        bullets: list[ResumeBullet] = []
        for b in result.bullets[:max_bullets]:
            bullets.append(
                ResumeBullet(
                    text=b.text,
                    bullet_type=self._parse_bullet_type(b.bullet_type),
                    action_verb=b.action_verb,
                    metrics=b.metrics,
                    keywords=b.keywords,
                    relevance_score=b.relevance_score,
                    original_text=achievements[b.original_index]
                    if b.original_index < len(achievements)
                    else None,
                )
            )

        while len(bullets) < min_bullets and len(bullets) < len(achievements):
            idx = len(bullets)
            bullets.append(
                ResumeBullet(
                    text=achievements[idx],
                    bullet_type=BulletType.GENERIC,
                    relevance_score=0.3,
                    original_text=achievements[idx],
                )
            )

        return bullets

    def _generate_summary(
        self,
        profile: PersonProfile,
        target_job_title: str | None,
        target_keywords: list[str] | None,
    ) -> str | None:
        current_title = None
        if profile.experiences:
            current = profile.get_current_position()
            current_title = current.title if current else profile.experiences[0].title

        top_achievements = []
        for exp in profile.experiences[:3]:
            top_achievements.extend(exp.achievements[:2])

        top_skills = [s.name for s in profile.skills[:10]]
        years_exp = profile.years_of_experience or profile.compute_years_of_experience()

        language = self._settings.output_language.value if self._settings else None
        prompt = build_professional_summary_prompt(
            name=profile.contact.full_name,
            current_title=current_title,
            years_experience=years_exp,
            top_skills=top_skills,
            top_achievements=top_achievements[:5],
            target_job_title=target_job_title,
            target_keywords=target_keywords,
            language=language,
        )

        try:
            result = self._call_claude_structured(prompt, ProfessionalSummarySchema)
            return result.summary
        except OptimizationError as e:
            logger.warning("Summary generation failed, using original: %s", e)
            return profile.professional_summary

    def _optimize_skills(
        self,
        profile: PersonProfile,
        target_keywords: list[str] | None,
    ) -> list[ResumeSkillGroup]:
        skills_data = [
            {
                "name": s.name,
                "category": s.category.value,
                "proficiency": s.proficiency,
                "years_experience": s.years_experience,
            }
            for s in profile.skills
        ]

        experiences_data = [
            {"title": exp.title, "technologies": exp.technologies} for exp in profile.experiences
        ]

        language = self._settings.output_language.value if self._settings else None
        prompt = build_skills_optimization_prompt(
            skills=skills_data,
            experiences=experiences_data,
            target_keywords=target_keywords,
            language=language,
        )

        try:
            result = self._call_claude_structured(prompt, SkillsOptimizationSchema)
            groups = []
            for g in sorted(result.skill_groups, key=lambda x: x.priority):
                groups.append(ResumeSkillGroup(category=g.category, skills=g.skills))
            return groups
        except OptimizationError as e:
            logger.warning("Skills optimization failed, using basic grouping: %s", e)
            return self._fallback_skill_groups(profile)

    def _fallback_skill_groups(self, profile: PersonProfile) -> list[ResumeSkillGroup]:
        groups: dict[str, list[str]] = {}
        for skill in profile.skills:
            cat = skill.category.value.title()
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(skill.name)

        return [ResumeSkillGroup(category=cat, skills=skills) for cat, skills in groups.items()]

    def _build_education(self, profile: PersonProfile) -> list[ResumeEducation]:
        return [
            ResumeEducation(
                institution=edu.institution,
                degree=f"{edu.degree} in {edu.field_of_study}"
                if edu.field_of_study
                else edu.degree,
                location=edu.location,
                graduation_date=edu.graduation_date,
                gpa=f"{edu.gpa:.2f}" if edu.gpa else None,
                honors=edu.honors,
                relevant_coursework=edu.relevant_coursework,
            )
            for edu in profile.education
        ]

    def _build_certifications(self, profile: PersonProfile) -> list[ResumeCertification]:
        return [
            ResumeCertification(
                name=f"{cert.name} ({cert.acronym})" if cert.acronym else cert.name,
                issuer=cert.issuing_organization,
                date_earned=cert.date_earned,
                credential_id=cert.credential_id,
            )
            for cert in profile.certifications
        ]

    def _build_projects(self, profile: PersonProfile) -> list[ResumeProject]:
        return [
            ResumeProject(
                name=proj.name,
                url=proj.url,
                description=proj.description,
                technologies=proj.technologies,
                highlights=proj.highlights,
            )
            for proj in profile.projects
        ]

    def _call_claude_structured(self, prompt: str, schema: type[T]) -> T:
        """Call Claude CLI and parse response into the specified schema.

        Args:
            prompt: The prompt to send to Claude.
            schema: A Pydantic model class defining the expected output structure.

        Returns:
            Parsed and validated instance of the schema.

        Raises:
            OptimizationError: If the CLI call or parsing fails.
        """
        full_prompt = build_prompt_with_schema(prompt, schema)

        try:
            result = self._cli.invoke(prompt=full_prompt, system=RESUME_OPTIMIZER_SYSTEM)
        except ClaudeCLIError as e:
            logger.exception("Claude CLI invocation failed")
            raise OptimizationError(f"Claude CLI error: {e}") from e

        if result.failed:
            raise OptimizationError(f"Claude CLI returned non-zero exit code: {result.exit_code}")

        try:
            data = parse_json_response(result.output)
        except ValueError as e:
            logger.error("Failed to parse JSON from Claude response: %s", e)
            raise OptimizationError(f"Failed to parse response: {e}") from e

        try:
            return schema.model_validate(data)
        except ValidationError as e:
            logger.error("Response validation failed: %s", e)
            raise OptimizationError(f"Response validation failed: {e}") from e

    @staticmethod
    def _parse_bullet_type(bullet_type: str) -> BulletType:
        type_map = {
            "xyz": BulletType.XYZ,
            "action_result": BulletType.ACTION_RESULT,
            "skill_based": BulletType.SKILL_BASED,
        }
        return type_map.get(bullet_type.lower(), BulletType.GENERIC)

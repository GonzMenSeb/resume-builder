"""Resume optimizer using Claude to transform PersonProfile into optimized ResumeDocument."""

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from anthropic import (
    Anthropic,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError

from resume_generator.config import Settings, get_settings
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

T = TypeVar("T")
logger = logging.getLogger(__name__)

STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 32.0


class OptimizationError(Exception):
    """Raised when resume optimization fails."""


def _is_retryable_error(error: Exception) -> bool:
    return isinstance(error, (APITimeoutError, APIConnectionError, RateLimitError))


def _exponential_backoff(attempt: int) -> float:
    backoff: float = INITIAL_BACKOFF_SECONDS * (2**attempt)
    return min(backoff, MAX_BACKOFF_SECONDS)


def _call_with_retry(func: Callable[[], T]) -> T:
    last_exception: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return func()
        except Exception as e:
            if not _is_retryable_error(e):
                raise
            last_exception = e
            if attempt == MAX_RETRIES - 1:
                logger.error("Max retries exceeded after %d attempts", MAX_RETRIES)
                raise
            wait_time = _exponential_backoff(attempt)
            logger.warning("Retryable error, waiting %.1fs: %s", wait_time, e)
            time.sleep(wait_time)
    if last_exception:
        raise last_exception
    raise AssertionError("Unexpected control flow in retry logic")


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
    """Transforms PersonProfile into optimized ResumeDocument using Claude AI."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = Anthropic(api_key=self._settings.anthropic_api_key.get_secret_value())

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
                )

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
    ) -> list[ResumeBullet]:
        prompt = build_bullet_batch_prompt(
            achievements=achievements,
            role_title=role_title,
            company=company,
            target_keywords=target_keywords,
        )

        try:
            result = self._call_claude_structured(prompt, BulletBatchResultSchema)
        except Exception as e:
            logger.warning("Bullet optimization failed, using original: %s", e)
            return [
                ResumeBullet(text=a, bullet_type=BulletType.GENERIC, relevance_score=0.5)
                for a in achievements[: self._settings.max_bullets_per_job]
            ]

        bullets: list[ResumeBullet] = []
        for b in result.bullets[: self._settings.max_bullets_per_job]:
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

        min_bullets = self._settings.min_bullets_per_job
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

        prompt = build_professional_summary_prompt(
            name=profile.contact.full_name,
            current_title=current_title,
            years_experience=years_exp,
            top_skills=top_skills,
            top_achievements=top_achievements[:5],
            target_job_title=target_job_title,
            target_keywords=target_keywords,
        )

        try:
            result = self._call_claude_structured(prompt, ProfessionalSummarySchema)
            return result.summary
        except Exception as e:
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

        prompt = build_skills_optimization_prompt(
            skills=skills_data,
            experiences=experiences_data,
            target_keywords=target_keywords,
        )

        try:
            result = self._call_claude_structured(prompt, SkillsOptimizationSchema)
            groups = []
            for g in sorted(result.skill_groups, key=lambda x: x.priority):
                groups.append(ResumeSkillGroup(category=g.category, skills=g.skills))
            return groups
        except Exception as e:
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
        def _api_call() -> T:
            response = self._client.beta.messages.parse(
                model=self._settings.claude_model.value,
                max_tokens=self._settings.max_tokens,
                betas=[STRUCTURED_OUTPUTS_BETA],
                system=RESUME_OPTIMIZER_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
            )
            if response.stop_reason == "refusal":
                raise OptimizationError("Claude refused to process this request")
            if response.stop_reason == "max_tokens":
                raise OptimizationError("Response truncated due to max_tokens limit")
            if response.parsed_output is None:
                raise OptimizationError("No parsed output received from Claude")
            return response.parsed_output

        try:
            return _call_with_retry(_api_call)
        except OptimizationError:
            raise
        except ValidationError as e:
            raise OptimizationError(f"Response validation failed: {e}") from e
        except Exception as e:
            logger.exception("Claude API call failed")
            raise OptimizationError(f"API call failed: {e}") from e

    @staticmethod
    def _parse_bullet_type(bullet_type: str) -> BulletType:
        type_map = {
            "xyz": BulletType.XYZ,
            "action_result": BulletType.ACTION_RESULT,
            "skill_based": BulletType.SKILL_BASED,
        }
        return type_map.get(bullet_type.lower(), BulletType.GENERIC)

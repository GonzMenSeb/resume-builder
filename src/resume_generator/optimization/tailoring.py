"""Job-specific resume tailoring for ATS optimization and keyword matching."""

import logging
import re
import time
from collections.abc import Callable
from typing import TypeVar

from anthropic import (
    Anthropic,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError

from resume_generator.config import Settings, get_settings
from resume_generator.models.job import JobDescription
from resume_generator.models.resume import (
    BulletType,
    ResumeBullet,
    ResumeDocument,
    ResumeExperience,
    ResumeSkillGroup,
)
from resume_generator.optimization.prompts import build_job_tailoring_prompt

T = TypeVar("T")
logger = logging.getLogger(__name__)

STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 32.0


class TailoringError(Exception):
    """Raised when resume tailoring fails."""


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


class TailoredExperienceSchema(BaseModel):
    company: str
    title: str
    bullets: list[str] = Field(description="Reordered and optimized bullets")
    relevance_score: float = Field(ge=0.0, le=1.0)


class TailoredSkillsSchema(BaseModel):
    reordered_groups: list[dict[str, list[str] | str]] = Field(
        description="Skill groups with category and skills"
    )
    added_keywords: list[str] = Field(default_factory=list)
    keyword_mapping: dict[str, str] = Field(default_factory=dict)


class KeywordAnalysisSchema(BaseModel):
    job_keywords: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    match_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    recommendations: list[str] = Field(default_factory=list)


class TailoringResultSchema(BaseModel):
    tailored_summary: str = Field(description="Updated professional summary")
    experiences: list[TailoredExperienceSchema] = Field(default_factory=list)
    skills: TailoredSkillsSchema
    keyword_analysis: KeywordAnalysisSchema
    overall_fit_score: float = Field(default=0.5, ge=0.0, le=1.0)


class KeywordMatch:
    """Represents a keyword match between resume and job."""

    def __init__(self, keyword: str, source: str, match_type: str = "exact"):
        self.keyword = keyword
        self.source = source
        self.match_type = match_type


class JobTailorer:
    """Optimizes resume content for specific job descriptions."""

    TAILORING_SYSTEM = """\
You are an expert ATS optimization specialist. Your task is to tailor resume content to
match specific job descriptions while maintaining truthfulness.

## Optimization Goals
- Target 65-80% keyword match rate
- Prioritize required skills and qualifications
- Use exact terminology from job posting where truthful
- Reorder content to highlight most relevant experience first

## Rules
1. NEVER fabricate experience or skills
2. Use job posting terminology for equivalent skills/technologies
3. Prioritize bullets that demonstrate required qualifications
4. Keep professional summary focused on role requirements
5. Ensure skills section matches job requirements ordering"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = Anthropic(api_key=self._settings.anthropic_api_key.get_secret_value())

    def tailor(
        self,
        resume: ResumeDocument,
        job: JobDescription,
        use_ai: bool = True,
    ) -> ResumeDocument:
        """
        Tailor a resume for a specific job description.

        Args:
            resume: The resume document to tailor.
            job: The target job description.
            use_ai: Whether to use Claude for enhanced tailoring.

        Returns:
            A new ResumeDocument tailored to the job.

        Raises:
            TailoringError: If tailoring fails.
        """
        job_keywords = self._extract_job_keywords(job)
        resume_keywords = resume.get_all_keywords()

        if use_ai and self._settings.enable_job_tailoring:
            return self._ai_tailor(resume, job, job_keywords)

        return self._rule_based_tailor(resume, job, job_keywords, resume_keywords)

    def analyze_keyword_match(
        self,
        resume: ResumeDocument,
        job: JobDescription,
    ) -> dict[str, list[str] | float | bool]:
        """
        Analyze keyword match between resume and job description.

        Returns a detailed analysis including match rate and recommendations.
        """
        job_keywords = self._extract_job_keywords(job)
        resume_keywords = resume.get_all_keywords()

        matches, missing = self._compute_keyword_overlap(job_keywords, resume_keywords)
        match_rate = len(matches) / len(job_keywords) if job_keywords else 0.0

        return {
            "job_keywords": list(job_keywords),
            "resume_keywords": list(resume_keywords),
            "matched": list(matches),
            "missing": list(missing),
            "match_rate": match_rate,
            "target_rate": self._settings.target_keyword_match_rate,
            "meets_target": match_rate >= self._settings.target_keyword_match_rate,
        }

    def score_experience_relevance(
        self,
        experience: ResumeExperience,
        job: JobDescription,
    ) -> float:
        """Score how relevant an experience entry is to the target job."""
        score = 0.0
        job_keywords = self._extract_job_keywords(job)
        job_keywords_lower = {kw.lower() for kw in job_keywords}

        title_words = set(experience.title.lower().split())
        job_title_words = set(job.title.lower().split())
        title_overlap = len(title_words & job_title_words)
        if title_overlap > 0:
            score += 0.3 * min(title_overlap / max(len(job_title_words), 1), 1.0)

        tech_match = sum(
            1 for t in experience.technologies if t.lower() in job_keywords_lower
        )
        if experience.technologies:
            score += 0.3 * min(tech_match / len(experience.technologies), 1.0)

        bullet_keywords: set[str] = set()
        for bullet in experience.bullets:
            bullet_keywords.update(kw.lower() for kw in bullet.keywords)
            for word in bullet.text.lower().split():
                if word in job_keywords_lower:
                    bullet_keywords.add(word)

        if job_keywords:
            bullet_match = len(bullet_keywords & job_keywords_lower)
            score += 0.4 * min(bullet_match / len(job_keywords), 1.0)

        return min(score, 1.0)

    def reorder_bullets_for_job(
        self,
        bullets: list[ResumeBullet],
        job: JobDescription,
    ) -> list[ResumeBullet]:
        """Reorder bullets by relevance to job, keeping most relevant first."""
        job_keywords = self._extract_job_keywords(job)
        job_keywords_lower = {kw.lower() for kw in job_keywords}

        def compute_bullet_relevance(bullet: ResumeBullet) -> float:
            score = bullet.relevance_score

            bullet_keywords_lower = {kw.lower() for kw in bullet.keywords}
            keyword_match = len(bullet_keywords_lower & job_keywords_lower)
            if job_keywords:
                score += 0.3 * (keyword_match / len(job_keywords))

            text_lower = bullet.text.lower()
            text_matches = sum(1 for kw in job_keywords_lower if kw in text_lower)
            if job_keywords:
                score += 0.2 * min(text_matches / len(job_keywords), 1.0)

            if bullet.has_metrics:
                score += 0.1

            return score

        scored = [(compute_bullet_relevance(b), b) for b in bullets]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            ResumeBullet(
                text=b.text,
                bullet_type=b.bullet_type,
                action_verb=b.action_verb,
                metrics=b.metrics,
                keywords=b.keywords,
                relevance_score=s,
                original_text=b.original_text,
            )
            for s, b in scored
        ]

    def customize_summary_for_job(
        self,
        summary: str | None,
        job: JobDescription,
        resume: ResumeDocument,
    ) -> str | None:
        """Customize professional summary to emphasize job-relevant qualifications."""
        if not summary:
            return None

        job_keywords = self._extract_job_keywords(job)
        job_keywords_lower = {kw.lower() for kw in job_keywords}

        summary_words = summary.lower().split()
        present_keywords = {w for w in summary_words if w in job_keywords_lower}

        if len(present_keywords) >= 3:
            return summary

        top_skills = []
        for group in resume.skills:
            for skill in group.skills:
                if skill.lower() in job_keywords_lower:
                    top_skills.append(skill)
                    if len(top_skills) >= 3:
                        break
            if len(top_skills) >= 3:
                break

        if not top_skills:
            return summary

        return summary

    def reorder_skills_for_job(
        self,
        skills: list[ResumeSkillGroup],
        job: JobDescription,
    ) -> list[ResumeSkillGroup]:
        """Reorder skill groups and skills within groups by job relevance."""
        job_keywords = self._extract_job_keywords(job)
        job_keywords_lower = {kw.lower() for kw in job_keywords}

        required_skills_lower = {s.lower() for s in job.required_skills}
        preferred_skills_lower = {s.lower() for s in job.preferred_skills}

        def score_skill(skill: str) -> int:
            s_lower = skill.lower()
            if s_lower in required_skills_lower:
                return 3
            if s_lower in preferred_skills_lower:
                return 2
            if s_lower in job_keywords_lower:
                return 1
            return 0

        def score_group(group: ResumeSkillGroup) -> tuple[int, int]:
            group_score = sum(score_skill(s) for s in group.skills)
            required_count = sum(1 for s in group.skills if s.lower() in required_skills_lower)
            return (required_count, group_score)

        reordered_groups = []
        for group in skills:
            scored_skills = [(score_skill(s), s) for s in group.skills]
            scored_skills.sort(key=lambda x: x[0], reverse=True)
            reordered_groups.append(
                ResumeSkillGroup(
                    category=group.category,
                    skills=[s for _, s in scored_skills],
                )
            )

        reordered_groups.sort(key=score_group, reverse=True)
        return reordered_groups

    def _extract_job_keywords(self, job: JobDescription) -> set[str]:
        """Extract all relevant keywords from a job description."""
        keywords: set[str] = set()

        keywords.update(job.required_skills)
        keywords.update(job.preferred_skills)
        keywords.update(job.required_certifications)

        for req in job.requirements:
            keywords.update(req.keywords)

        title_words = self._extract_significant_words(job.title)
        keywords.update(title_words)

        if job.description:
            tech_keywords = self._extract_tech_keywords(job.description)
            keywords.update(tech_keywords)

        return {kw for kw in keywords if len(kw) > 1}

    def _extract_significant_words(self, text: str) -> set[str]:
        """Extract significant words (likely job-related terms) from text."""
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
            "be", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall", "can", "need",
            "we", "you", "they", "he", "she", "it", "i", "our", "your", "their",
        }
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]*\b", text)
        return {w for w in words if w.lower() not in stop_words and len(w) > 2}

    def _extract_tech_keywords(self, text: str) -> set[str]:
        """Extract technology-related keywords from text."""
        tech_patterns = [
            r"\b[A-Z][a-zA-Z]+(?:JS|DB|ML|AI|API|SDK|UI|UX)\b",
            r"\b(?:Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin)\b",
            r"\b(?:React|Angular|Vue|Node|Django|Flask|Spring|Rails|Laravel)\b",
            r"\b(?:AWS|GCP|Azure|Docker|Kubernetes|Terraform|Jenkins|GitHub)\b",
            r"\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Kafka)\b",
            r"\b(?:REST|GraphQL|gRPC|OAuth|JWT|SAML)\b",
        ]
        keywords: set[str] = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.update(matches)
        return keywords

    def _compute_keyword_overlap(
        self,
        job_keywords: set[str],
        resume_keywords: set[str],
    ) -> tuple[set[str], set[str]]:
        """Compute matched and missing keywords between job and resume."""
        job_lower = {kw.lower() for kw in job_keywords}
        resume_lower = {kw.lower() for kw in resume_keywords}

        matched = job_lower & resume_lower
        missing = job_lower - resume_lower

        return matched, missing

    def _rule_based_tailor(
        self,
        resume: ResumeDocument,
        job: JobDescription,
        job_keywords: set[str],
        resume_keywords: set[str],
    ) -> ResumeDocument:
        """Apply rule-based tailoring without AI assistance."""
        tailored_experiences = []
        for exp in resume.experiences:
            reordered_bullets = self.reorder_bullets_for_job(exp.bullets, job)

            tailored_experiences.append(
                ResumeExperience(
                    company=exp.company,
                    title=exp.title,
                    location=exp.location,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    bullets=reordered_bullets,
                    technologies=exp.technologies,
                )
            )

        tailored_experiences.sort(
            key=lambda e: self.score_experience_relevance(e, job),
            reverse=True,
        )

        tailored_skills = self.reorder_skills_for_job(resume.skills, job)
        tailored_summary = self.customize_summary_for_job(
            resume.professional_summary, job, resume
        )

        matches, _ = self._compute_keyword_overlap(job_keywords, resume_keywords)
        match_rate = len(matches) / len(job_keywords) if job_keywords else 0.0

        return ResumeDocument(
            contact=resume.contact,
            professional_summary=tailored_summary,
            headline=resume.headline,
            experiences=tailored_experiences,
            education=resume.education,
            skills=tailored_skills,
            certifications=resume.certifications,
            projects=resume.projects,
            additional_sections=resume.additional_sections,
            target_job_title=job.title,
            keyword_match_rate=match_rate,
            optimization_score=resume.optimization_score,
        )

    def _ai_tailor(
        self,
        resume: ResumeDocument,
        job: JobDescription,
        job_keywords: set[str],
    ) -> ResumeDocument:
        """Apply AI-enhanced tailoring using Claude."""
        resume_content = self._resume_to_dict(resume)
        job_content = self._job_to_dict(job)

        prompt = build_job_tailoring_prompt(resume_content, job_content)

        try:
            result = self._call_claude_structured(prompt, TailoringResultSchema)
        except Exception as e:
            logger.warning("AI tailoring failed, falling back to rule-based: %s", e)
            return self._rule_based_tailor(
                resume, job, job_keywords, resume.get_all_keywords()
            )

        return self._apply_tailoring_result(resume, job, result)

    def _resume_to_dict(self, resume: ResumeDocument) -> dict[str, object]:
        """Convert resume to dictionary for prompt building."""
        return {
            "professional_summary": resume.professional_summary,
            "experiences": [
                {
                    "company": exp.company,
                    "title": exp.title,
                    "bullets": [b.text for b in exp.bullets],
                    "technologies": exp.technologies,
                }
                for exp in resume.experiences
            ],
            "skills": [
                {"category": g.category, "skills": g.skills}
                for g in resume.skills
            ],
        }

    def _job_to_dict(self, job: JobDescription) -> dict[str, object]:
        """Convert job description to dictionary for prompt building."""
        return {
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "requirements": [
                {
                    "text": r.text,
                    "priority": r.priority.value,
                    "keywords": r.keywords,
                }
                for r in job.requirements
            ],
            "responsibilities": job.responsibilities,
        }

    def _apply_tailoring_result(
        self,
        resume: ResumeDocument,
        job: JobDescription,
        result: TailoringResultSchema,
    ) -> ResumeDocument:
        """Apply AI tailoring result to create new resume document."""
        exp_map = {e.company: i for i, e in enumerate(resume.experiences)}

        tailored_experiences = []
        for tailored_exp in result.experiences:
            orig_idx = exp_map.get(tailored_exp.company)
            if orig_idx is None:
                continue

            orig = resume.experiences[orig_idx]
            new_bullets = []

            for i, bullet_text in enumerate(tailored_exp.bullets):
                orig_bullet = orig.bullets[i] if i < len(orig.bullets) else None
                new_bullets.append(
                    ResumeBullet(
                        text=bullet_text,
                        bullet_type=orig_bullet.bullet_type if orig_bullet else BulletType.GENERIC,
                        action_verb=orig_bullet.action_verb if orig_bullet else None,
                        metrics=orig_bullet.metrics if orig_bullet else {},
                        keywords=orig_bullet.keywords if orig_bullet else [],
                        relevance_score=tailored_exp.relevance_score,
                        original_text=orig_bullet.text if orig_bullet else None,
                    )
                )

            tailored_experiences.append(
                ResumeExperience(
                    company=orig.company,
                    title=orig.title,
                    location=orig.location,
                    start_date=orig.start_date,
                    end_date=orig.end_date,
                    is_current=orig.is_current,
                    bullets=new_bullets if new_bullets else orig.bullets,
                    technologies=orig.technologies,
                )
            )

        for exp in resume.experiences:
            if exp.company not in [e.company for e in tailored_experiences]:
                tailored_experiences.append(exp)

        tailored_skills = []
        for group_data in result.skills.reordered_groups:
            category = group_data.get("category", "")
            skills_list = group_data.get("skills", [])
            if category and skills_list and isinstance(skills_list, list):
                tailored_skills.append(
                    ResumeSkillGroup(category=str(category), skills=skills_list)
                )

        if not tailored_skills:
            tailored_skills = resume.skills

        return ResumeDocument(
            contact=resume.contact,
            professional_summary=result.tailored_summary or resume.professional_summary,
            headline=resume.headline,
            experiences=tailored_experiences,
            education=resume.education,
            skills=tailored_skills,
            certifications=resume.certifications,
            projects=resume.projects,
            additional_sections=resume.additional_sections,
            target_job_title=job.title,
            keyword_match_rate=result.keyword_analysis.match_rate,
            optimization_score=result.overall_fit_score,
        )

    def _call_claude_structured(self, prompt: str, schema: type[T]) -> T:
        """Call Claude API with structured output."""

        def _api_call() -> T:
            response = self._client.beta.messages.parse(
                model=self._settings.claude_model.value,
                max_tokens=self._settings.max_tokens,
                betas=[STRUCTURED_OUTPUTS_BETA],
                system=self.TAILORING_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
            )
            if response.stop_reason == "refusal":
                raise TailoringError("Claude refused to process this request")
            if response.stop_reason == "max_tokens":
                raise TailoringError("Response truncated due to max_tokens limit")
            if response.parsed_output is None:
                raise TailoringError("No parsed output received from Claude")
            return response.parsed_output

        try:
            return _call_with_retry(_api_call)
        except TailoringError:
            raise
        except ValidationError as e:
            raise TailoringError(f"Response validation failed: {e}") from e
        except Exception as e:
            logger.exception("Claude API call failed")
            raise TailoringError(f"API call failed: {e}") from e

"""Resume polisher agent that addresses critique feedback and improves content."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError

from resume_generator.claude_client import (
    ClaudeCLI,
    ClaudeCLIError,
    build_prompt_with_schema,
    parse_json_response,
)
from resume_generator.models.resume import (
    ResumeDocument,
    ResumeExperience,
    ResumeBullet,
    BulletType,
    ResumeSkillGroup,
)
from resume_generator.refinement.critique import CritiqueResult

if TYPE_CHECKING:
    from resume_generator.config import Settings

logger = logging.getLogger(__name__)


class PolishError(Exception):
    """Raised when resume polishing fails."""


class PolishedBulletSchema(BaseModel):
    """Schema for a polished bullet point."""

    text: str = Field(description="Improved bullet text")
    action_verb: str = Field(default="", description="Leading action verb")
    keywords: list[str] = Field(default_factory=list, description="ATS keywords")


class PolishedExperienceSchema(BaseModel):
    """Schema for polished experience section."""

    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    bullets: list[PolishedBulletSchema] = Field(description="Improved bullets")


class PolishedSkillGroupSchema(BaseModel):
    """Schema for polished skill group."""

    category: str = Field(description="Category name")
    skills: list[str] = Field(description="Skills in category")


class PolishResponseSchema(BaseModel):
    """Schema for polish response."""

    professional_summary: str = Field(description="Improved professional summary")
    experiences: list[PolishedExperienceSchema] = Field(description="Improved experiences")
    skills: list[PolishedSkillGroupSchema] = Field(description="Reorganized skills")
    changes_made: list[str] = Field(default_factory=list, description="List of changes made")
    issues_addressed: list[str] = Field(
        default_factory=list, description="Which critique issues were addressed"
    )


@dataclass
class PolishResult:
    """Result of resume polishing."""

    resume: ResumeDocument
    changes_made: list[str]
    issues_addressed: list[str]


POLISHER_SYSTEM_PROMPT = """You are an expert resume writer specializing in transforming good resumes into exceptional ones.

Your task is to polish a resume based on specific critique feedback. You must:
1. Address each issue raised by the critique
2. Preserve the factual content while improving presentation
3. Apply research-backed best practices
4. Maintain professional tone and clarity
5. CRITICALLY IMPORTANT: Preserve the original language of the resume. If the resume is in Spanish, keep ALL content in Spanish. If in English, keep in English.

## Key Principles
- Use the X-Y-Z formula: "Accomplished [X] as measured by [Y] by doing [Z]"
- Start bullets with strong, varied action verbs
- Quantify achievements with specific metrics
- Keep bullets concise (under 25-30 words)
- Professional summary should be 50-100 words, value-focused
- Group and prioritize skills by relevance

DO NOT fabricate information. Only rephrase and restructure existing content.
NEVER change the language of the resume content.
"""


def _build_polish_prompt(
    resume: ResumeDocument,
    critique: CritiqueResult,
    language: str | None = None,
    raw_text: str | None = None,
) -> str:
    """Build the polish prompt with resume content, critique feedback, and original raw data."""
    experiences_json = []
    for exp in resume.experiences:
        experiences_json.append({
            "company": exp.company,
            "title": exp.title,
            "bullets": [b.text for b in exp.bullets],
        })

    skills_json = [{"category": g.category, "skills": g.skills} for g in resume.skills]

    raw_data_section = ""
    if raw_text:
        truncated_raw = raw_text[:20000] if len(raw_text) > 20000 else raw_text
        raw_data_section = f"""
## ORIGINAL RAW DATA (Source Material)
The following is the original raw data. You can use this to:
- Recover valuable information that was omitted due to space constraints
- Find specific metrics and achievements to add
- Ensure you're not fabricating information

<raw_data>
{truncated_raw}
</raw_data>
"""

    missing_info_section = ""
    if critique.missing_valuable_info:
        missing_info_section = f"""
**Valuable Information That Was Omitted (from raw data):**
{chr(10).join(f"- {info}" for info in critique.missing_valuable_info)}
Consider re-adding this information if space allows.
"""

    exaggeration_section = ""
    if critique.exaggeration_issues:
        exaggeration_section = f"""
**Exaggeration Issues to Fix (CRITICAL):**
{chr(10).join(f"- {issue}" for issue in critique.exaggeration_issues)}
These claims appear exaggerated or unsupported. Tone them down to match the raw data.
"""

    base_prompt = f"""Polish this resume to address the critique feedback.

## Current Resume Content

**Professional Summary:**
{resume.professional_summary or "None provided"}

**Experiences:**
{experiences_json}

**Skills:**
{skills_json}
{raw_data_section}
## Critique Feedback

**Current Grade:** {critique.grade.value}
**Justification:** {critique.justification}

**Issues to Address:**
{chr(10).join(f"- {issue}" for issue in critique.issues)}

**Priority Improvements:**
{chr(10).join(f"- {imp}" for imp in critique.improvement_priorities)}
{missing_info_section}{exaggeration_section}
**Scores:**
- Content: {critique.content_score:.0%}
- Design: {critique.design_score:.0%}
- ATS: {critique.ats_score:.0%}
- Truthfulness: {critique.truthfulness_score:.0%}

## Instructions

1. Rewrite the professional summary to be more impactful (50-100 words)
2. Improve each experience bullet using X-Y-Z formula where possible
3. Reorganize skills for better ATS compatibility
4. Address all issues raised in the critique
5. CRITICAL: Only use information from the raw data - do NOT fabricate metrics or achievements
6. If valuable info was omitted, try to incorporate it back
7. If exaggerations were flagged, tone them down to match raw data
8. CRITICAL: Keep the SAME language as the original resume content

{f"IMPORTANT: The resume content is in {language.upper()} - ALL output MUST be in {language.upper()}. Do NOT translate to English or any other language." if language and language != "en" else ""}

Return the polished content in the SAME LANGUAGE as the input."""

    return build_prompt_with_schema(base_prompt, PolishResponseSchema)


class ResumePolisher:
    """Polishes resumes based on critique feedback."""

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

    def polish(
        self,
        resume: ResumeDocument,
        critique: CritiqueResult,
        raw_text: str | None = None,
    ) -> PolishResult:
        """Polish a resume based on critique feedback.

        Args:
            resume: The ResumeDocument to polish.
            critique: The critique feedback to address.
            raw_text: Original raw data for recovering omitted information.

        Returns:
            PolishResult with improved resume and list of changes.

        Raises:
            PolishError: If polishing fails.
        """
        logger.info(
            "Polishing resume: %d issues, %d priorities",
            len(critique.issues),
            len(critique.improvement_priorities),
        )
        language = self._settings.output_language.value if self._settings else None
        prompt = _build_polish_prompt(resume, critique, language, raw_text)

        try:
            result = self._cli.invoke(prompt=prompt, system=POLISHER_SYSTEM_PROMPT)
        except ClaudeCLIError as e:
            logger.exception("Claude CLI polish invocation failed")
            raise PolishError(f"Polish failed: {e}") from e

        if result.failed:
            raise PolishError(f"Polish returned non-zero exit code: {result.exit_code}")

        try:
            data = parse_json_response(result.output)
        except ValueError as e:
            logger.error("Failed to parse polish JSON: %s", e)
            raise PolishError(f"Failed to parse polish response: {e}") from e

        try:
            response = PolishResponseSchema.model_validate(data)
        except ValidationError as e:
            logger.error("Polish response validation failed: %s", e)
            raise PolishError(f"Polish validation failed: {e}") from e

        logger.info(
            "Polish result: %d changes, %d issues addressed",
            len(response.changes_made),
            len(response.issues_addressed),
        )
        logger.debug("Changes made: %s", response.changes_made)
        logger.debug("Issues addressed: %s", response.issues_addressed)

        polished_resume = self._apply_polish(resume, response)

        return PolishResult(
            resume=polished_resume,
            changes_made=response.changes_made,
            issues_addressed=response.issues_addressed,
        )

    def _apply_polish(
        self,
        original: ResumeDocument,
        polished: PolishResponseSchema,
    ) -> ResumeDocument:
        """Apply polished content to create a new ResumeDocument."""
        polished_exp_map = {
            (e.company.lower(), e.title.lower()): e for e in polished.experiences
        }

        new_experiences: list[ResumeExperience] = []
        for orig_exp in original.experiences:
            key = (orig_exp.company.lower(), orig_exp.title.lower())
            if key in polished_exp_map:
                logger.debug("Applying polish to experience: %s at %s", orig_exp.title, orig_exp.company)
                pol_exp = polished_exp_map[key]
                new_bullets = [
                    ResumeBullet(
                        text=b.text,
                        bullet_type=BulletType.XYZ if "%" in b.text or any(c.isdigit() for c in b.text) else BulletType.ACTION_RESULT,
                        action_verb=b.action_verb,
                        keywords=b.keywords,
                        relevance_score=0.8,
                    )
                    for b in pol_exp.bullets
                ]
                new_experiences.append(
                    ResumeExperience(
                        company=orig_exp.company,
                        title=orig_exp.title,
                        location=orig_exp.location,
                        start_date=orig_exp.start_date,
                        end_date=orig_exp.end_date,
                        is_current=orig_exp.is_current,
                        bullets=new_bullets if new_bullets else orig_exp.bullets,
                        technologies=orig_exp.technologies,
                    )
                )
            else:
                new_experiences.append(orig_exp)

        new_skills = [
            ResumeSkillGroup(category=g.category, skills=g.skills)
            for g in polished.skills
        ] if polished.skills else original.skills

        return ResumeDocument(
            contact=original.contact,
            professional_summary=polished.professional_summary or original.professional_summary,
            headline=original.headline,
            experiences=new_experiences,
            education=original.education,
            skills=new_skills,
            certifications=original.certifications,
            projects=original.projects,
            target_job_title=original.target_job_title,
            optimization_score=original.optimization_score,
            keyword_match_rate=original.keyword_match_rate,
        )

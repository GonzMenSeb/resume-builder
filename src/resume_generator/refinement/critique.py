"""Resume critique agent that evaluates PDF quality and assigns tier grades."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError

from resume_generator.claude_client import (
    ClaudeCLI,
    ClaudeCLIError,
    build_prompt_with_schema,
    parse_json_response,
)
from resume_generator.config import TierGrade, parse_tier_grade

if TYPE_CHECKING:
    from resume_generator.config import Settings

logger = logging.getLogger(__name__)


class CritiqueError(Exception):
    """Raised when resume critique fails."""


class CritiqueResponseSchema(BaseModel):
    """Schema for critique response."""

    grade: str = Field(description="Tier grade: S+, S, A+, A, A-, B+, B, B-, C+, C, C-, D, F")
    justification: str = Field(description="Detailed justification for the grade")
    issues: list[str] = Field(default_factory=list, description="Specific issues found")
    strengths: list[str] = Field(default_factory=list, description="Strong points of the resume")
    improvement_priorities: list[str] = Field(
        default_factory=list, description="Prioritized list of improvements"
    )
    content_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Content quality 0-1")
    design_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Visual design quality 0-1"
    )
    ats_score: float = Field(default=0.5, ge=0.0, le=1.0, description="ATS compatibility 0-1")
    truthfulness_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How truthful the resume is compared to raw data (1.0 = fully truthful)",
    )
    exaggeration_issues: list[str] = Field(
        default_factory=list,
        description="Specific claims that appear exaggerated or unsupported by raw data",
    )
    missing_valuable_info: list[str] = Field(
        default_factory=list,
        description="Valuable information from raw data that was omitted from the resume",
    )
    max_achievable_grade: str = Field(
        default="S+", description="Maximum grade achievable given the quality/quantity of raw data"
    )
    grade_ceiling_reason: str = Field(
        default="",
        description="Explanation of why a higher grade cannot be achieved (if applicable)",
    )


@dataclass
class CritiqueResult:
    """Result of a resume critique."""

    grade: TierGrade
    justification: str
    issues: list[str]
    strengths: list[str]
    improvement_priorities: list[str]
    content_score: float
    design_score: float
    ats_score: float
    truthfulness_score: float = 1.0
    exaggeration_issues: list[str] = field(default_factory=list)
    missing_valuable_info: list[str] = field(default_factory=list)
    max_achievable_grade: TierGrade | None = None
    grade_ceiling_reason: str = ""

    @property
    def overall_score(self) -> float:
        return (
            self.content_score + self.design_score + self.ats_score + self.truthfulness_score
        ) / 4

    @property
    def target_unattainable(self) -> bool:
        """Check if the max achievable grade indicates target may be unattainable."""
        return self.max_achievable_grade is not None and self.grade_ceiling_reason != ""


CRITIQUE_SYSTEM_PROMPT = """You are an expert resume reviewer and hiring manager with deep knowledge of:
- Resume best practices and industry standards
- Applicant Tracking Systems (ATS) and keyword optimization
- Visual design principles for professional documents
- Content strategy for career advancement

Your task is to critically evaluate a PDF resume against research-backed criteria and assign a tier grade.

## Grading Scale
- S+: Exceptional - Perfect or near-perfect execution, ready for executive/top-tier applications
- S: Outstanding - Excellent quality, minor improvements possible but not required
- A+: Excellent - High quality with minimal issues
- A: Very Good - Strong resume with small areas for improvement
- A-: Good - Solid resume with some noticeable improvements needed
- B+: Above Average - Decent but has several issues to address
- B: Average - Acceptable but needs significant improvement
- B-: Below Average - Multiple issues that hurt effectiveness
- C+: Fair - Notable problems affecting readability or impact
- C: Poor - Significant issues throughout
- C-: Very Poor - Major problems making it largely ineffective
- D: Bad - Fundamental issues with structure or content
- F: Failing - Does not meet basic resume standards

Be strict but fair. Most resumes should fall in the B to A range. Reserve S grades for truly exceptional documents.

## CRITICAL: Truth-Seeker Role
You will be given the ORIGINAL RAW DATA that the resume was built from. You MUST:
1. Verify that claims in the resume are supported by the raw data
2. Penalize exaggeration, embellishment, or fabrication severely
3. Flag any metrics/achievements that appear inflated beyond what raw data supports
4. Note valuable information from raw data that was omitted from the resume

A resume that lies or exaggerates significantly should NEVER receive above a C grade, regardless of how polished it looks.

## Maximum Achievable Grade Assessment
Based on the quality and quantity of the raw data provided, assess the MAXIMUM grade this resume could realistically achieve. Consider:
- Is there enough substantial work experience?
- Are there quantifiable achievements in the raw data?
- Is the career trajectory impressive enough for high grades?

If the raw data is thin, generic, or lacks impressive achievements, the max achievable grade may be B or lower. Be honest about this ceiling.
"""


def _load_research_criteria(research_dir: Path) -> str:
    """Load research documents to inform critique criteria."""
    criteria_text = ""

    if not research_dir.exists():
        logger.warning("Research directory not found: %s", research_dir)
        return criteria_text

    for tex_file in sorted(research_dir.glob("*.tex")):
        try:
            content = tex_file.read_text(encoding="utf-8")
            doc_name = tex_file.stem.replace("_", " ").title()
            criteria_text += f"\n\n## {doc_name}\n{content[:15000]}"
        except Exception as e:
            logger.warning("Could not read %s: %s", tex_file, e)

    return criteria_text


def _build_critique_prompt(
    pdf_path: Path, research_criteria: str, raw_text: str | None = None
) -> str:
    """Build the critique prompt with research criteria and optional raw data for truth verification."""
    raw_data_section = ""
    if raw_text:
        truncated_raw = raw_text[:20000] if len(raw_text) > 20000 else raw_text
        raw_data_section = f"""
## ORIGINAL RAW DATA (Source of Truth)
The following is the original raw data from which this resume was built. Use this to verify truthfulness.

<raw_data>
{truncated_raw}
</raw_data>

Compare the resume claims against this raw data. Flag any:
- Exaggerated metrics or achievements
- Claims not supported by the raw data
- Fabricated information
- Valuable information from raw data that was omitted
"""

    base_prompt = f"""Critically evaluate the resume PDF at: {pdf_path}

Read and analyze the PDF thoroughly. Evaluate it against the following research-based criteria:

{research_criteria}
{raw_data_section}

## Evaluation Areas

1. **Content Quality** (30% weight)
   - Professional summary effectiveness (50-100 words, value-focused)
   - Achievement bullets (X-Y-Z formula, quantified metrics)
   - Action verbs (strong, varied, not "responsible for")
   - Keywords and ATS optimization
   - Skills presentation (grouped, relevant)

2. **Visual Design** (25% weight)
   - Layout and white space (30:70 content-to-space ratio ideal)
   - Typography (10-12pt body, clear hierarchy)
   - Margins (0.5-1 inch)
   - Section organization and headers
   - Consistency throughout

3. **ATS Compatibility** (20% weight)
   - Standard section headers
   - Parseable format
   - No problematic graphics/icons
   - Contact info in body (not header/footer)
   - File format appropriateness

4. **Truthfulness** (25% weight) - CRITICAL
   - All claims must be verifiable from raw data
   - Metrics must match or be reasonable interpretations of raw data
   - No fabricated achievements or inflated numbers
   - Omission of valuable raw data information is also a problem

## Maximum Achievable Grade
Based on the raw data quality, determine the MAXIMUM grade this resume could achieve:
- If raw data has impressive, quantifiable achievements → max could be S+ or S
- If raw data is solid but not exceptional → max is likely A range
- If raw data is thin or generic → max may be B range or lower
- If raw data is very limited → max may be C range

Set max_achievable_grade accordingly and explain in grade_ceiling_reason if it's below S+.

Assign a tier grade based on overall quality. Be critical but constructive.
Identify specific issues that can be fixed and prioritize improvements.

IMPORTANT: The resume may be in a language other than English. Evaluate it based on the quality standards regardless of language. Do NOT penalize for being in a non-English language."""

    return build_prompt_with_schema(base_prompt, CritiqueResponseSchema)


class ResumeCritique:
    """Evaluates PDF resumes and assigns tier grades based on research criteria."""

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

        self._research_criteria: str | None = None

    def _get_research_criteria(self) -> str:
        """Load research criteria lazily."""
        if self._research_criteria is None:
            research_dir = (
                self._settings.refinement_research_dir
                if self._settings
                else Path(__file__).parent.parent.parent / "docs" / "research-results" / "tex"
            )
            self._research_criteria = _load_research_criteria(research_dir)
        return self._research_criteria

    def critique(self, pdf_path: Path, raw_text: str | None = None) -> CritiqueResult:
        """Critique a PDF resume and return a tier grade with justification.

        Args:
            pdf_path: Path to the PDF resume to evaluate.
            raw_text: Original raw data for truth verification.

        Returns:
            CritiqueResult with grade, justification, and improvement areas.

        Raises:
            CritiqueError: If critique fails.
        """
        if not pdf_path.exists():
            raise CritiqueError(f"PDF not found: {pdf_path}")

        logger.info("Critiquing PDF: %s", pdf_path)
        criteria = self._get_research_criteria()
        logger.debug("Loaded research criteria: %d chars", len(criteria))
        prompt = _build_critique_prompt(pdf_path, criteria, raw_text)

        logger.debug(
            "Prompting RESUME_CRITIQUE: pdf=%s, research_criteria_chars=%d, has_raw_text=%s",
            pdf_path.name,
            len(criteria),
            raw_text is not None,
        )
        try:
            result = self._cli.invoke(
                prompt=prompt,
                system=CRITIQUE_SYSTEM_PROMPT,
                working_dir=pdf_path.parent,
            )
        except ClaudeCLIError as e:
            logger.exception("Claude CLI critique invocation failed")
            raise CritiqueError(f"Critique failed: {e}") from e

        if result.failed:
            raise CritiqueError(f"Critique returned non-zero exit code: {result.exit_code}")

        try:
            data = parse_json_response(result.output)
        except ValueError as e:
            logger.error("Failed to parse critique JSON: %s", e)
            raise CritiqueError(f"Failed to parse critique response: {e}") from e

        try:
            response = CritiqueResponseSchema.model_validate(data)
        except ValidationError as e:
            logger.error("Critique response validation failed: %s", e)
            raise CritiqueError(f"Critique validation failed: {e}") from e

        grade = parse_tier_grade(response.grade)
        if grade is None:
            logger.warning("Invalid grade '%s' from critique, defaulting to B", response.grade)
            grade = TierGrade.B

        max_grade = parse_tier_grade(response.max_achievable_grade)
        if max_grade is None:
            max_grade = TierGrade.S_PLUS

        logger.info(
            "Critique grade: %s (content=%.0f%%, design=%.0f%%, ats=%.0f%%, truth=%.0f%%)",
            grade.value,
            response.content_score * 100,
            response.design_score * 100,
            response.ats_score * 100,
            response.truthfulness_score * 100,
        )
        logger.debug("Issues:\n%s", "\n".join(f"  - {item}" for item in response.issues))
        logger.debug(
            "Improvement priorities:\n%s",
            "\n".join(f"  - {item}" for item in response.improvement_priorities),
        )
        logger.debug("Strengths:\n%s", "\n".join(f"  - {item}" for item in response.strengths))
        if response.exaggeration_issues:
            logger.info("Exaggeration issues: %s", response.exaggeration_issues)
        if response.missing_valuable_info:
            logger.info("Missing valuable info: %s", response.missing_valuable_info)
        if max_grade and response.grade_ceiling_reason:
            logger.info(
                "Max achievable grade: %s (%s)", max_grade.value, response.grade_ceiling_reason
            )

        return CritiqueResult(
            grade=grade,
            justification=response.justification,
            issues=response.issues,
            strengths=response.strengths,
            improvement_priorities=response.improvement_priorities,
            content_score=response.content_score,
            design_score=response.design_score,
            ats_score=response.ats_score,
            truthfulness_score=response.truthfulness_score,
            exaggeration_issues=response.exaggeration_issues,
            missing_valuable_info=response.missing_valuable_info,
            max_achievable_grade=max_grade,
            grade_ceiling_reason=response.grade_ceiling_reason,
        )

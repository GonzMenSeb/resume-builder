"""Job-specific resume tailoring for ATS optimization and keyword matching."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, Field, ValidationError

from resume_generator.claude_client import (
    ClaudeCLI,
    ClaudeCLIError,
    build_prompt_with_schema,
    parse_json_response,
)
from resume_generator.models.job import JobDescription
from resume_generator.models.resume import (
    BulletType,
    ResumeBullet,
    ResumeDocument,
    ResumeExperience,
    ResumeSkillGroup,
)
from resume_generator.optimization.prompts import (
    JOB_TAILORING_SYSTEM,
    build_job_tailoring_prompt,
)

if TYPE_CHECKING:
    from resume_generator.config import Settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

WEIGHT_REQUIRED = 3.0
WEIGHT_PREFERRED = 2.0
WEIGHT_GENERAL = 1.0
WEIGHT_EXACT_MATCH = 1.0
WEIGHT_FUZZY_MATCH = 0.7
WEIGHT_PARTIAL_MATCH = 0.5
FUZZY_MATCH_THRESHOLD = 0.85

ACRONYM_EXPANSIONS: dict[str, list[str]] = {
    "ml": ["machine learning"],
    "ai": ["artificial intelligence"],
    "dl": ["deep learning"],
    "nlp": ["natural language processing"],
    "cv": ["computer vision"],
    "api": ["application programming interface"],
    "rest": ["representational state transfer"],
    "sql": ["structured query language"],
    "nosql": ["non-relational database", "non relational database"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud platform"],
    "ci": ["continuous integration"],
    "cd": ["continuous delivery", "continuous deployment"],
    "cicd": ["continuous integration continuous deployment", "ci/cd"],
    "devops": ["development operations"],
    "k8s": ["kubernetes"],
    "js": ["javascript"],
    "ts": ["typescript"],
    "py": ["python"],
    "db": ["database"],
    "ui": ["user interface"],
    "ux": ["user experience"],
    "qa": ["quality assurance"],
    "tdd": ["test driven development"],
    "bdd": ["behavior driven development"],
    "oop": ["object oriented programming"],
    "fp": ["functional programming"],
    "sre": ["site reliability engineering"],
    "swe": ["software engineer", "software engineering"],
    "sde": ["software development engineer"],
    "pm": ["project manager", "product manager"],
    "saas": ["software as a service"],
    "paas": ["platform as a service"],
    "iaas": ["infrastructure as a service"],
    "vpc": ["virtual private cloud"],
    "ec2": ["elastic compute cloud"],
    "s3": ["simple storage service"],
    "rds": ["relational database service"],
    "iam": ["identity and access management"],
    "jwt": ["json web token"],
    "oauth": ["open authorization"],
    "sso": ["single sign on"],
    "rbac": ["role based access control"],
    "etl": ["extract transform load"],
    "elt": ["extract load transform"],
    "olap": ["online analytical processing"],
    "oltp": ["online transaction processing"],
    "llm": ["large language model"],
    "rag": ["retrieval augmented generation"],
}


class TailoringError(Exception):
    """Raised when resume tailoring fails."""


@dataclass
class KeywordMatchResult:
    """Detailed result of a single keyword match."""

    job_keyword: str
    resume_keyword: str | None
    match_type: str
    weight: float
    is_required: bool

    @property
    def matched(self) -> bool:
        return self.resume_keyword is not None


@dataclass
class MatchAnalysis:
    """Complete keyword match analysis between resume and job."""

    job_keywords: list[str]
    resume_keywords: list[str]
    matches: list[KeywordMatchResult]
    match_rate: float
    weighted_score: float
    required_match_rate: float
    preferred_match_rate: float
    missing_required: list[str]
    missing_preferred: list[str]
    recommendations: list[str]
    meets_target: bool


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


class JobTailorer:
    """Optimizes resume content for specific job descriptions using Claude CLI."""

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

    def tailor(
        self,
        resume: ResumeDocument,
        job: JobDescription,
        use_ai: bool = True,
    ) -> ResumeDocument:
        """Tailor a resume for a specific job description.

        Args:
            resume: The resume document to tailor.
            job: The target job description.
            use_ai: Whether to use Claude for enhanced tailoring.

        Returns:
            A new ResumeDocument tailored to the job.

        Raises:
            TailoringError: If tailoring fails.
        """
        logger.info("Tailoring resume for '%s' (ai=%s)", job.title, use_ai)
        job_keywords = self._extract_job_keywords(job)
        resume_keywords = resume.get_all_keywords()

        if use_ai and self._settings and self._settings.enable_job_tailoring:
            return self._ai_tailor(resume, job, job_keywords)

        return self._rule_based_tailor(resume, job, job_keywords, resume_keywords)

    def analyze_keyword_match(
        self,
        resume: ResumeDocument,
        job: JobDescription,
    ) -> dict[str, list[str] | float | bool]:
        """Analyze keyword match between resume and job description.

        Returns a detailed analysis including match rate and recommendations.
        """
        job_keywords = self._extract_job_keywords(job)
        resume_keywords = resume.get_all_keywords()

        matches, missing = self._compute_keyword_overlap(job_keywords, resume_keywords)
        match_rate = len(matches) / len(job_keywords) if job_keywords else 0.0

        target_rate = self._settings.target_keyword_match_rate if self._settings else 0.65

        return {
            "job_keywords": list(job_keywords),
            "resume_keywords": list(resume_keywords),
            "matched": list(matches),
            "missing": list(missing),
            "match_rate": match_rate,
            "target_rate": target_rate,
            "meets_target": match_rate >= target_rate,
        }

    def analyze_keyword_match_detailed(
        self,
        resume: ResumeDocument,
        job: JobDescription,
    ) -> MatchAnalysis:
        """Perform comprehensive keyword match analysis with weighted scoring.

        Uses fuzzy matching, acronym expansion, and weighted scoring based on
        keyword importance (required vs preferred).

        Returns:
            MatchAnalysis with detailed breakdown and actionable recommendations.
        """
        weighted_keywords = self.extract_keywords_detailed(job)
        resume_keywords = resume.get_all_keywords()
        resume_keywords_lower = {kw.lower() for kw in resume_keywords}

        resume_text_lower = self._get_resume_text(resume).lower()

        matches: list[KeywordMatchResult] = []
        required_matched = 0
        required_total = 0
        preferred_matched = 0
        preferred_total = 0

        for job_kw, (_, weight) in weighted_keywords.items():
            is_required = weight >= WEIGHT_REQUIRED
            if is_required:
                required_total += 1
            else:
                preferred_total += 1

            match_result = self._find_best_match(
                job_kw, resume_keywords, resume_keywords_lower, resume_text_lower
            )

            if match_result:
                resume_kw, match_type, match_weight = match_result
                matches.append(
                    KeywordMatchResult(
                        job_keyword=job_kw,
                        resume_keyword=resume_kw,
                        match_type=match_type,
                        weight=weight * match_weight,
                        is_required=is_required,
                    )
                )
                if is_required:
                    required_matched += 1
                else:
                    preferred_matched += 1
            else:
                matches.append(
                    KeywordMatchResult(
                        job_keyword=job_kw,
                        resume_keyword=None,
                        match_type="none",
                        weight=0.0,
                        is_required=is_required,
                    )
                )

        total_keywords = len(weighted_keywords)
        matched_count = sum(1 for m in matches if m.matched)
        match_rate = matched_count / total_keywords if total_keywords > 0 else 0.0

        max_possible_score = sum(w for _, (_, w) in weighted_keywords.items())
        actual_score = sum(m.weight for m in matches if m.matched)
        weighted_score = actual_score / max_possible_score if max_possible_score > 0 else 0.0

        required_match_rate = required_matched / required_total if required_total > 0 else 1.0
        preferred_match_rate = preferred_matched / preferred_total if preferred_total > 0 else 1.0

        missing_required = [m.job_keyword for m in matches if not m.matched and m.is_required]
        missing_preferred = [m.job_keyword for m in matches if not m.matched and not m.is_required]

        target_rate = self._settings.target_keyword_match_rate if self._settings else 0.65

        recommendations = self._generate_recommendations(
            match_rate,
            weighted_score,
            missing_required,
            missing_preferred,
            target_rate,
        )

        logger.info(
            "Keyword match: rate=%.0f%%, weighted=%.0f%%, missing=%d",
            match_rate * 100,
            weighted_score * 100,
            len(missing_required) + len(missing_preferred),
        )

        return MatchAnalysis(
            job_keywords=list(weighted_keywords.keys()),
            resume_keywords=list(resume_keywords),
            matches=matches,
            match_rate=match_rate,
            weighted_score=weighted_score,
            required_match_rate=required_match_rate,
            preferred_match_rate=preferred_match_rate,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            recommendations=recommendations,
            meets_target=match_rate >= target_rate,
        )

    def _find_best_match(
        self,
        job_keyword: str,
        resume_keywords: set[str],
        resume_keywords_lower: set[str],
        resume_text_lower: str,
    ) -> tuple[str, str, float] | None:
        """Find the best match for a job keyword in the resume.

        Returns:
            Tuple of (matched_keyword, match_type, match_weight) or None.
        """
        job_kw_lower = job_keyword.lower()

        if job_kw_lower in resume_keywords_lower:
            for kw in resume_keywords:
                if kw.lower() == job_kw_lower:
                    return (kw, "exact", WEIGHT_EXACT_MATCH)

        expansions = ACRONYM_EXPANSIONS.get(job_kw_lower, [])
        for expansion in expansions:
            if expansion in resume_text_lower:
                return (expansion, "acronym_expansion", WEIGHT_EXACT_MATCH)

        for acronym, exps in ACRONYM_EXPANSIONS.items():
            if job_kw_lower in exps and acronym in resume_keywords_lower:
                for kw in resume_keywords:
                    if kw.lower() == acronym:
                        return (kw, "acronym_match", WEIGHT_EXACT_MATCH)

        best_fuzzy: tuple[str, float] | None = None
        for kw in resume_keywords:
            ratio = SequenceMatcher(None, job_kw_lower, kw.lower()).ratio()
            if ratio >= FUZZY_MATCH_THRESHOLD and (best_fuzzy is None or ratio > best_fuzzy[1]):
                best_fuzzy = (kw, ratio)

        if best_fuzzy:
            return (best_fuzzy[0], "fuzzy", WEIGHT_FUZZY_MATCH)

        if len(job_kw_lower) > 3 and job_kw_lower in resume_text_lower:
            return (job_keyword, "text_contains", WEIGHT_PARTIAL_MATCH)

        return None

    def _get_resume_text(self, resume: ResumeDocument) -> str:
        """Extract all text content from resume for full-text matching."""
        parts: list[str] = []

        if resume.professional_summary:
            parts.append(resume.professional_summary)

        for exp in resume.experiences:
            parts.append(exp.title)
            parts.append(exp.company)
            for bullet in exp.bullets:
                parts.append(bullet.text)
            parts.extend(exp.technologies)

        for edu in resume.education:
            parts.append(edu.degree)
            parts.append(edu.institution)

        for group in resume.skills:
            parts.extend(group.skills)

        for cert in resume.certifications:
            parts.append(cert.name)
            if cert.issuer:
                parts.append(cert.issuer)

        for project in resume.projects:
            parts.append(project.name)
            if project.description:
                parts.append(project.description)
            parts.extend(project.technologies)

        return " ".join(parts)

    def _generate_recommendations(
        self,
        match_rate: float,
        weighted_score: float,
        missing_required: list[str],
        missing_preferred: list[str],
        target_rate: float,
    ) -> list[str]:
        """Generate actionable recommendations based on match analysis."""
        recommendations: list[str] = []

        if missing_required:
            top_missing = missing_required[:5]
            recommendations.append(f"Add missing required skills: {', '.join(top_missing)}")

        if match_rate < target_rate:
            gap = int((target_rate - match_rate) * 100)
            recommendations.append(
                f"Increase keyword match rate by {gap}% to reach target of {int(target_rate * 100)}%"
            )

        if missing_preferred and match_rate >= target_rate * 0.8:
            top_preferred = missing_preferred[:3]
            recommendations.append(f"Consider adding preferred skills: {', '.join(top_preferred)}")

        if weighted_score < 0.5 and match_rate >= 0.5:
            recommendations.append(
                "Focus on high-priority keywords (required skills) over general matches"
            )

        if not recommendations and match_rate >= target_rate:
            recommendations.append(
                f"Good match rate ({int(match_rate * 100)}%) - resume is well-aligned with job requirements"
            )

        return recommendations

    def calculate_match_score(
        self,
        resume: ResumeDocument,
        job: JobDescription,
    ) -> float:
        """Calculate a normalized match score (0.0 to 1.0) between resume and job.

        This combines keyword matching with weighted scoring based on requirement priority.
        """
        analysis = self.analyze_keyword_match_detailed(resume, job)
        return (analysis.match_rate * 0.6) + (analysis.weighted_score * 0.4)

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

        tech_match = sum(1 for t in experience.technologies if t.lower() in job_keywords_lower)
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
                relevance_score=min(s, 1.0),
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

            bigrams = self._extract_bigrams(job.description)
            keywords.update(bigrams)

        for resp in job.responsibilities:
            resp_keywords = self._extract_tech_keywords(resp)
            keywords.update(resp_keywords)

        return {kw for kw in keywords if len(kw) > 1}

    def extract_keywords_detailed(self, job: JobDescription) -> dict[str, tuple[set[str], float]]:
        """Extract keywords with their category and weight.

        Returns dict mapping keyword to (sources, weight).
        """
        result: dict[str, tuple[set[str], float]] = {}

        for skill in job.required_skills:
            normalized = skill.strip()
            if normalized:
                if normalized in result:
                    sources, _ = result[normalized]
                    sources.add("required_skills")
                else:
                    result[normalized] = ({"required_skills"}, WEIGHT_REQUIRED)

        for skill in job.preferred_skills:
            normalized = skill.strip()
            if normalized:
                if normalized in result:
                    sources, weight = result[normalized]
                    sources.add("preferred_skills")
                else:
                    result[normalized] = ({"preferred_skills"}, WEIGHT_PREFERRED)

        for cert in job.required_certifications:
            normalized = cert.strip()
            if normalized:
                if normalized in result:
                    sources, weight = result[normalized]
                    sources.add("certifications")
                    result[normalized] = (sources, max(weight, WEIGHT_REQUIRED))
                else:
                    result[normalized] = ({"certifications"}, WEIGHT_REQUIRED)

        for req in job.requirements:
            for kw in req.keywords:
                normalized = kw.strip()
                if normalized:
                    weight = (
                        WEIGHT_REQUIRED if req.priority.value == "required" else WEIGHT_PREFERRED
                    )
                    if normalized in result:
                        sources, existing_weight = result[normalized]
                        sources.add("requirements")
                        result[normalized] = (sources, max(existing_weight, weight))
                    else:
                        result[normalized] = ({"requirements"}, weight)

        if job.description:
            for kw in self._extract_tech_keywords(job.description):
                if kw not in result:
                    result[kw] = ({"description"}, WEIGHT_GENERAL)

        return {k: v for k, v in result.items() if len(k) > 1}

    def _extract_bigrams(self, text: str) -> set[str]:
        """Extract meaningful two-word phrases (bigrams) from text."""
        bigram_patterns = [
            r"\b(machine\s+learning)\b",
            r"\b(deep\s+learning)\b",
            r"\b(natural\s+language\s+processing)\b",
            r"\b(computer\s+vision)\b",
            r"\b(data\s+science)\b",
            r"\b(data\s+engineering)\b",
            r"\b(software\s+engineering)\b",
            r"\b(software\s+development)\b",
            r"\b(web\s+development)\b",
            r"\b(mobile\s+development)\b",
            r"\b(cloud\s+computing)\b",
            r"\b(distributed\s+systems)\b",
            r"\b(microservices?\s+architecture)\b",
            r"\b(agile\s+methodology)\b",
            r"\b(project\s+management)\b",
            r"\b(product\s+management)\b",
            r"\b(version\s+control)\b",
            r"\b(test\s+driven\s+development)\b",
            r"\b(continuous\s+integration)\b",
            r"\b(continuous\s+deployment)\b",
            r"\b(object\s+oriented\s+programming)\b",
            r"\b(functional\s+programming)\b",
            r"\b(system\s+design)\b",
            r"\b(api\s+design)\b",
            r"\b(database\s+design)\b",
            r"\b(full\s+stack)\b",
            r"\b(front\s*end)\b",
            r"\b(back\s*end)\b",
            r"\b(site\s+reliability)\b",
            r"\b(user\s+experience)\b",
            r"\b(user\s+interface)\b",
            r"\b(quality\s+assurance)\b",
            r"\b(code\s+review)\b",
            r"\b(pair\s+programming)\b",
        ]

        bigrams: set[str] = set()
        text_lower = text.lower()

        for pattern in bigram_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                normalized = re.sub(r"\s+", " ", match).strip()
                bigrams.add(normalized)

        return bigrams

    def _extract_significant_words(self, text: str) -> set[str]:
        """Extract significant words (likely job-related terms) from text."""
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "we",
            "you",
            "they",
            "he",
            "she",
            "it",
            "i",
            "our",
            "your",
            "their",
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
        logger.info("Using rule-based tailoring fallback")
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
        tailored_summary = self.customize_summary_for_job(resume.professional_summary, job, resume)

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
        """Apply AI-enhanced tailoring using Claude CLI."""
        resume_content = self._resume_to_dict(resume)
        job_content = self._job_to_dict(job)

        language = self._settings.output_language.value if self._settings else None
        customization_rate = self._settings.tailoring_customization_rate if self._settings else None
        prompt = build_job_tailoring_prompt(
            resume_content, job_content, language=language, customization_rate=customization_rate
        )

        logger.debug(
            "Prompting JOB_TAILORING: job_title=%s, customization_rate=%s, language=%s",
            job.title,
            customization_rate,
            language,
        )
        try:
            result = self._call_claude_structured(prompt, TailoringResultSchema)
        except TailoringError as e:
            logger.warning("AI tailoring failed, falling back to rule-based: %s", e)
            return self._rule_based_tailor(resume, job, job_keywords, resume.get_all_keywords())

        logger.info(
            "AI tailoring result: fit_score=%.0f%%, match_rate=%.0f%%",
            result.overall_fit_score * 100,
            result.keyword_analysis.match_rate * 100,
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
            "skills": [{"category": g.category, "skills": g.skills} for g in resume.skills],
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
                tailored_skills.append(ResumeSkillGroup(category=str(category), skills=skills_list))

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
        """Call Claude CLI and parse response into the specified schema.

        Args:
            prompt: The prompt to send to Claude.
            schema: A Pydantic model class defining the expected output structure.

        Returns:
            Parsed and validated instance of the schema.

        Raises:
            TailoringError: If the CLI call or parsing fails.
        """
        full_prompt = build_prompt_with_schema(prompt, schema)

        try:
            result = self._cli.invoke(prompt=full_prompt, system=JOB_TAILORING_SYSTEM)
        except ClaudeCLIError as e:
            logger.exception("Claude CLI invocation failed")
            raise TailoringError(f"Claude CLI error: {e}") from e

        if result.failed:
            raise TailoringError(f"Claude CLI returned non-zero exit code: {result.exit_code}")

        try:
            data = parse_json_response(result.output)
        except ValueError as e:
            logger.error("Failed to parse JSON from Claude response: %s", e)
            raise TailoringError(f"Failed to parse response: {e}") from e

        try:
            return schema.model_validate(data)
        except ValidationError as e:
            logger.error("Response validation failed: %s", e)
            raise TailoringError(f"Response validation failed: {e}") from e

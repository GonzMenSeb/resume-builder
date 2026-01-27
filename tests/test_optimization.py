"""Unit tests for optimization module."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from anthropic import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import SecretStr

from resume_generator.config import Settings
from resume_generator.models.job import JobDescription
from resume_generator.models.profile import PersonProfile
from resume_generator.models.resume import (
    BulletType,
    ResumeBullet,
    ResumeDocument,
    ResumeExperience,
    ResumeSkillGroup,
)
from resume_generator.optimization.optimizer import (
    BulletBatchResultSchema,
    OptimizationError,
    OptimizedBulletSchema,
    ProfessionalSummarySchema,
    ResumeOptimizer,
    SkillGroupSchema,
    SkillsOptimizationSchema,
    _call_with_retry,
    _exponential_backoff,
    _is_retryable_error,
)
from resume_generator.optimization.tailoring import (
    JobTailorer,
    KeywordMatchResult,
    MatchAnalysis,
)
from resume_generator.optimization.tailoring import (
    _call_with_retry as tailoring_call_with_retry,
)
from resume_generator.optimization.tailoring import (
    _exponential_backoff as tailoring_exponential_backoff,
)
from resume_generator.optimization.tailoring import (
    _is_retryable_error as tailoring_is_retryable_error,
)


class TestOptimizerRetryHelpers:
    """Tests for optimizer retry helper functions."""

    def test_is_retryable_error_timeout(self) -> None:
        mock_request = MagicMock()
        error = APITimeoutError(request=mock_request)
        assert _is_retryable_error(error)

    def test_is_retryable_error_connection(self) -> None:
        mock_request = MagicMock()
        error = APIConnectionError(message="connection", request=mock_request)
        assert _is_retryable_error(error)

    def test_is_retryable_error_rate_limit(self) -> None:
        mock_response = MagicMock()
        error = RateLimitError("rate limit", response=mock_response, body=None)
        assert _is_retryable_error(error)

    def test_is_retryable_error_generic_exception(self) -> None:
        assert not _is_retryable_error(ValueError("not retryable"))

    def test_exponential_backoff_initial(self) -> None:
        assert _exponential_backoff(0) == 1.0

    def test_exponential_backoff_second_attempt(self) -> None:
        assert _exponential_backoff(1) == 2.0

    def test_exponential_backoff_max_limit(self) -> None:
        assert _exponential_backoff(10) == 32.0

    def test_call_with_retry_success_first_try(self) -> None:
        mock_func = MagicMock(return_value="success")
        result = _call_with_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_call_with_retry_success_after_retry(self) -> None:
        mock_request = MagicMock()
        error = APITimeoutError(request=mock_request)
        mock_func = MagicMock(side_effect=[error, "success"])
        with patch("time.sleep"):
            result = _call_with_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 2

    def test_call_with_retry_non_retryable_error(self) -> None:
        mock_func = MagicMock(side_effect=ValueError("bad input"))
        with pytest.raises(ValueError, match="bad input"):
            _call_with_retry(mock_func)
        assert mock_func.call_count == 1

    def test_call_with_retry_max_attempts_exceeded(self) -> None:
        mock_request = MagicMock()
        error = APITimeoutError(request=mock_request)
        mock_func = MagicMock(side_effect=error)
        with patch("time.sleep"), pytest.raises(APITimeoutError):
            _call_with_retry(mock_func)
        assert mock_func.call_count == 3


class TestResumeOptimizer:
    """Tests for ResumeOptimizer class."""

    def test_init_with_settings(self, test_settings: Settings) -> None:
        optimizer = ResumeOptimizer(settings=test_settings)
        assert optimizer._settings == test_settings
        assert optimizer._client is not None

    def test_init_without_settings(self) -> None:
        with patch("resume_generator.optimization.optimizer.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.anthropic_api_key = SecretStr("sk-test-key")
            mock_get_settings.return_value = mock_settings
            optimizer = ResumeOptimizer()
            assert optimizer._settings == mock_settings

    def test_build_contact(self, sample_person_profile: PersonProfile) -> None:
        optimizer = ResumeOptimizer(settings=Settings(anthropic_api_key="sk-test"))
        contact = optimizer._build_contact(sample_person_profile)
        assert contact.name == "Jane Doe"
        assert contact.email == "jane.doe@example.com"
        assert contact.phone == "+1-555-0123"
        assert contact.location == "San Francisco, CA"

    def test_build_education(self, sample_person_profile: PersonProfile) -> None:
        optimizer = ResumeOptimizer(settings=Settings(anthropic_api_key="sk-test"))
        education = optimizer._build_education(sample_person_profile)
        assert len(education) == 1
        assert education[0].institution == "Stanford University"
        assert education[0].degree == "Bachelor of Science in Computer Science"
        assert education[0].gpa == "3.80"

    def test_build_certifications(self, sample_person_profile: PersonProfile) -> None:
        optimizer = ResumeOptimizer(settings=Settings(anthropic_api_key="sk-test"))
        certs = optimizer._build_certifications(sample_person_profile)
        assert len(certs) == 1
        assert certs[0].name == "AWS Certified Solutions Architect (AWS-SAA)"
        assert certs[0].issuer == "Amazon Web Services"

    def test_build_projects(self, sample_person_profile: PersonProfile) -> None:
        optimizer = ResumeOptimizer(settings=Settings(anthropic_api_key="sk-test"))
        projects = optimizer._build_projects(sample_person_profile)
        assert len(projects) == 1
        assert projects[0].name == "Open Source ML Framework"
        assert "Python" in projects[0].technologies

    def test_parse_bullet_type_xyz(self) -> None:
        assert ResumeOptimizer._parse_bullet_type("xyz") == BulletType.XYZ

    def test_parse_bullet_type_action_result(self) -> None:
        assert ResumeOptimizer._parse_bullet_type("action_result") == BulletType.ACTION_RESULT

    def test_parse_bullet_type_skill_based(self) -> None:
        assert ResumeOptimizer._parse_bullet_type("skill_based") == BulletType.SKILL_BASED

    def test_parse_bullet_type_generic_fallback(self) -> None:
        assert ResumeOptimizer._parse_bullet_type("unknown") == BulletType.GENERIC

    def test_fallback_skill_groups(self, sample_person_profile: PersonProfile) -> None:
        optimizer = ResumeOptimizer(settings=Settings(anthropic_api_key="sk-test"))
        groups = optimizer._fallback_skill_groups(sample_person_profile)
        assert len(groups) > 0
        categories = {g.category for g in groups}
        assert "Programming" in categories or "Technical" in categories

    def test_optimize_bullets_fallback_on_error(
        self, test_settings: Settings, sample_person_profile: PersonProfile
    ) -> None:
        optimizer = ResumeOptimizer(settings=test_settings)
        with patch.object(optimizer, "_call_claude_structured", side_effect=Exception("API error")):
            bullets = optimizer._optimize_bullets(
                achievements=["Built something", "Improved performance"],
                role_title="Engineer",
                company="Tech Corp",
                target_keywords=None,
            )
            assert len(bullets) >= 2
            assert all(isinstance(b, ResumeBullet) for b in bullets)

    def test_optimize_experiences_no_achievements(
        self, test_settings: Settings, sample_contact_info
    ) -> None:
        from resume_generator.models.profile import Experience

        profile = PersonProfile(
            contact=sample_contact_info,
            experiences=[
                Experience(
                    company="Test Co",
                    title="Engineer",
                    start_date=date(2020, 1, 1),
                    achievements=[],
                    description="Software development work with various technologies",
                )
            ],
            skills=[],
            education=[],
        )

        optimizer = ResumeOptimizer(settings=test_settings)
        experiences = optimizer._optimize_experiences(profile, None)
        assert len(experiences) == 1
        assert len(experiences[0].bullets) >= 1
        assert experiences[0].bullets[0].bullet_type == BulletType.GENERIC

    def test_optimize_summary_fallback(
        self, test_settings: Settings, sample_person_profile: PersonProfile
    ) -> None:
        optimizer = ResumeOptimizer(settings=test_settings)
        with patch.object(optimizer, "_call_claude_structured", side_effect=Exception("API error")):
            summary = optimizer._generate_summary(sample_person_profile, None, None)
            assert summary == sample_person_profile.professional_summary

    def test_optimize_skills_fallback(
        self, test_settings: Settings, sample_person_profile: PersonProfile
    ) -> None:
        optimizer = ResumeOptimizer(settings=test_settings)
        with patch.object(optimizer, "_call_claude_structured", side_effect=Exception("API error")):
            skills = optimizer._optimize_skills(sample_person_profile, None)
            assert len(skills) > 0

    @patch("resume_generator.optimization.optimizer.Anthropic")
    def test_call_claude_structured_success(self, mock_anthropic: MagicMock, test_settings: Settings) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        parsed_output = ProfessionalSummarySchema(
            summary="Test summary",
            word_count=10,
            keywords_included=["Python"],
            tailored_for_job=False,
        )
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.parsed_output = parsed_output
        mock_client.beta.messages.parse.return_value = mock_response

        optimizer = ResumeOptimizer(settings=test_settings)
        result = optimizer._call_claude_structured("test prompt", ProfessionalSummarySchema)
        assert result.summary == "Test summary"
        assert result.word_count == 10

    @patch("resume_generator.optimization.optimizer.Anthropic")
    def test_call_claude_structured_refusal(self, mock_anthropic: MagicMock, test_settings: Settings) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.stop_reason = "refusal"
        mock_client.beta.messages.parse.return_value = mock_response

        optimizer = ResumeOptimizer(settings=test_settings)
        with pytest.raises(OptimizationError, match="refused to process"):
            optimizer._call_claude_structured("test prompt", ProfessionalSummarySchema)

    @patch("resume_generator.optimization.optimizer.Anthropic")
    def test_call_claude_structured_max_tokens(self, mock_anthropic: MagicMock, test_settings: Settings) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.stop_reason = "max_tokens"
        mock_client.beta.messages.parse.return_value = mock_response

        optimizer = ResumeOptimizer(settings=test_settings)
        with pytest.raises(OptimizationError, match="truncated due to max_tokens"):
            optimizer._call_claude_structured("test prompt", ProfessionalSummarySchema)

    @patch("resume_generator.optimization.optimizer.Anthropic")
    def test_call_claude_structured_no_output(self, mock_anthropic: MagicMock, test_settings: Settings) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.parsed_output = None
        mock_client.beta.messages.parse.return_value = mock_response

        optimizer = ResumeOptimizer(settings=test_settings)
        with pytest.raises(OptimizationError, match="No parsed output"):
            optimizer._call_claude_structured("test prompt", ProfessionalSummarySchema)

    @patch("resume_generator.optimization.optimizer.Anthropic")
    def test_optimize_full_pipeline(
        self, mock_anthropic: MagicMock, test_settings: Settings, sample_person_profile: PersonProfile
    ) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        bullet_result = BulletBatchResultSchema(
            bullets=[
                OptimizedBulletSchema(
                    text="Improved system performance by 50%",
                    action_verb="Improved",
                    bullet_type="action_result",
                    has_metrics=True,
                    metrics={"improvement": "50%"},
                    keywords=["performance"],
                    relevance_score=0.9,
                    original_index=0,
                )
            ],
            overall_quality_score=0.9,
        )

        summary_result = ProfessionalSummarySchema(
            summary="Senior engineer with proven track record",
            word_count=6,
            keywords_included=["Python", "AWS"],
            tailored_for_job=True,
        )

        skills_result = SkillsOptimizationSchema(
            skill_groups=[
                SkillGroupSchema(category="Languages", skills=["Python", "Go"], priority=1)
            ],
            total_skills_count=2,
        )

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.parsed_output = None

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                mock_response.parsed_output = bullet_result
            elif call_count[0] == 2:
                mock_response.parsed_output = summary_result
            else:
                mock_response.parsed_output = skills_result
            return mock_response

        mock_client.beta.messages.parse.side_effect = side_effect

        optimizer = ResumeOptimizer(settings=test_settings)
        result = optimizer.optimize(sample_person_profile, target_job_title="Senior Engineer")

        assert isinstance(result, ResumeDocument)
        assert result.contact.name == "Jane Doe"
        assert result.target_job_title == "Senior Engineer"
        assert len(result.experiences) > 0
        assert result.optimization_score > 0


class TestTailorerRetryHelpers:
    """Tests for tailorer retry helper functions."""

    def test_is_retryable_error_timeout(self) -> None:
        mock_request = MagicMock()
        error = APITimeoutError(request=mock_request)
        assert tailoring_is_retryable_error(error)

    def test_is_retryable_error_connection(self) -> None:
        mock_request = MagicMock()
        error = APIConnectionError(message="connection", request=mock_request)
        assert tailoring_is_retryable_error(error)

    def test_exponential_backoff(self) -> None:
        assert tailoring_exponential_backoff(0) == 1.0
        assert tailoring_exponential_backoff(1) == 2.0
        assert tailoring_exponential_backoff(10) == 32.0

    def test_call_with_retry_success(self) -> None:
        mock_func = MagicMock(return_value="success")
        result = tailoring_call_with_retry(mock_func)
        assert result == "success"


class TestJobTailorer:
    """Tests for JobTailorer class."""

    def test_init_with_settings(self, test_settings: Settings) -> None:
        tailorer = JobTailorer(settings=test_settings)
        assert tailorer._settings == test_settings
        assert tailorer._client is not None

    def test_extract_job_keywords(self, sample_job_description: JobDescription) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        keywords = tailorer._extract_job_keywords(sample_job_description)
        assert "Python" in keywords
        assert "AWS" in keywords
        assert "Docker" in keywords
        assert "Kubernetes" in keywords

    def test_extract_keywords_detailed(self, sample_job_description: JobDescription) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        detailed_keywords = tailorer.extract_keywords_detailed(sample_job_description)
        assert "Python" in detailed_keywords
        sources, weight = detailed_keywords["Python"]
        assert "required_skills" in sources
        assert weight >= 2.0

    def test_compute_keyword_overlap(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        job_kw = {"Python", "AWS", "Docker"}
        resume_kw = {"Python", "Docker", "React"}
        matched, missing = tailorer._compute_keyword_overlap(job_kw, resume_kw)
        assert matched == {"python", "docker"}
        assert missing == {"aws"}

    def test_analyze_keyword_match(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        analysis = tailorer.analyze_keyword_match(sample_resume_document, sample_job_description)
        assert "job_keywords" in analysis
        assert "resume_keywords" in analysis
        assert "matched" in analysis
        assert "missing" in analysis
        assert "match_rate" in analysis
        assert isinstance(analysis["match_rate"], float)

    def test_analyze_keyword_match_detailed(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        analysis = tailorer.analyze_keyword_match_detailed(sample_resume_document, sample_job_description)
        assert isinstance(analysis, MatchAnalysis)
        assert len(analysis.job_keywords) > 0
        assert analysis.match_rate >= 0.0
        assert analysis.weighted_score >= 0.0

    def test_calculate_match_score(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        score = tailorer.calculate_match_score(sample_resume_document, sample_job_description)
        assert 0.0 <= score <= 1.0

    def test_score_experience_relevance(
        self, sample_resume_experience: ResumeExperience, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        score = tailorer.score_experience_relevance(sample_resume_experience, sample_job_description)
        assert 0.0 <= score <= 1.0

    def test_reorder_bullets_for_job(
        self, sample_resume_experience: ResumeExperience, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        reordered = tailorer.reorder_bullets_for_job(
            sample_resume_experience.bullets, sample_job_description
        )
        assert len(reordered) == len(sample_resume_experience.bullets)
        assert all(isinstance(b, ResumeBullet) for b in reordered)
        assert reordered[0].relevance_score >= reordered[-1].relevance_score

    def test_reorder_skills_for_job(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        reordered = tailorer.reorder_skills_for_job(sample_resume_document.skills, sample_job_description)
        assert len(reordered) == len(sample_resume_document.skills)
        assert all(isinstance(g, ResumeSkillGroup) for g in reordered)

    def test_customize_summary_for_job(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        summary = tailorer.customize_summary_for_job(
            sample_resume_document.professional_summary,
            sample_job_description,
            sample_resume_document,
        )
        assert summary is not None
        assert isinstance(summary, str)

    def test_customize_summary_for_job_none_input(self, sample_job_description: JobDescription) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        resume = MagicMock()
        resume.skills = []
        summary = tailorer.customize_summary_for_job(None, sample_job_description, resume)
        assert summary is None

    def test_extract_significant_words(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        words = tailorer._extract_significant_words("Python Developer with AWS experience")
        assert "Python" in words
        assert "Developer" in words
        assert "AWS" in words
        assert "with" not in words

    def test_extract_tech_keywords(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        keywords = tailorer._extract_tech_keywords(
            "Experience with Python, React, AWS, and PostgreSQL required"
        )
        assert "Python" in keywords
        assert "React" in keywords
        assert "AWS" in keywords
        assert "PostgreSQL" in keywords

    def test_extract_bigrams(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        bigrams = tailorer._extract_bigrams(
            "We need machine learning and cloud computing expertise"
        )
        assert "machine learning" in bigrams
        assert "cloud computing" in bigrams

    def test_get_resume_text(self, sample_resume_document: ResumeDocument) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        text = tailorer._get_resume_text(sample_resume_document)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "Jane Doe" in text or "Senior Software Engineer" in text

    def test_find_best_match_exact(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        resume_kw = {"Python", "AWS", "Docker"}
        resume_kw_lower = {kw.lower() for kw in resume_kw}
        resume_text_lower = "python aws docker kubernetes"

        match = tailorer._find_best_match("Python", resume_kw, resume_kw_lower, resume_text_lower)
        assert match is not None
        assert match[0] == "Python"
        assert match[1] == "exact"

    def test_find_best_match_fuzzy(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        resume_kw = {"Kubernetes"}
        resume_kw_lower = {kw.lower() for kw in resume_kw}
        resume_text_lower = "kubernetes experience"

        match = tailorer._find_best_match("k8s", resume_kw, resume_kw_lower, resume_text_lower)
        assert match is not None

    def test_find_best_match_no_match(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        resume_kw = {"Python"}
        resume_kw_lower = {kw.lower() for kw in resume_kw}
        resume_text_lower = "python only"

        match = tailorer._find_best_match("Rust", resume_kw, resume_kw_lower, resume_text_lower)
        assert match is None

    def test_generate_recommendations_missing_required(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        recommendations = tailorer._generate_recommendations(
            match_rate=0.5,
            weighted_score=0.6,
            missing_required=["Python", "AWS"],
            missing_preferred=["Go"],
            target_rate=0.65,
        )
        assert len(recommendations) > 0
        assert any("required" in r.lower() for r in recommendations)

    def test_generate_recommendations_good_match(self) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        recommendations = tailorer._generate_recommendations(
            match_rate=0.8,
            weighted_score=0.85,
            missing_required=[],
            missing_preferred=[],
            target_rate=0.65,
        )
        assert len(recommendations) > 0
        assert any("Good match" in r for r in recommendations)

    def test_rule_based_tailor(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        job_keywords = tailorer._extract_job_keywords(sample_job_description)
        resume_keywords = sample_resume_document.get_all_keywords()

        tailored = tailorer._rule_based_tailor(
            sample_resume_document, sample_job_description, job_keywords, resume_keywords
        )

        assert isinstance(tailored, ResumeDocument)
        assert tailored.target_job_title == sample_job_description.title
        assert tailored.keyword_match_rate >= 0.0

    def test_tailor_with_ai_disabled(
        self, sample_resume_document: ResumeDocument, sample_job_description: JobDescription
    ) -> None:
        settings = Settings(anthropic_api_key="sk-test", enable_job_tailoring=False)
        tailorer = JobTailorer(settings=settings)
        tailored = tailorer.tailor(sample_resume_document, sample_job_description, use_ai=False)
        assert isinstance(tailored, ResumeDocument)
        assert tailored.target_job_title == sample_job_description.title

    @patch("resume_generator.optimization.tailoring.Anthropic")
    def test_tailor_with_ai_fallback_on_error(
        self,
        mock_anthropic: MagicMock,
        sample_resume_document: ResumeDocument,
        sample_job_description: JobDescription,
    ) -> None:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.beta.messages.parse.side_effect = Exception("API error")

        settings = Settings(anthropic_api_key="sk-test", enable_job_tailoring=True)
        tailorer = JobTailorer(settings=settings)
        tailored = tailorer.tailor(sample_resume_document, sample_job_description, use_ai=True)

        assert isinstance(tailored, ResumeDocument)
        assert tailored.target_job_title == sample_job_description.title

    def test_resume_to_dict(self, sample_resume_document: ResumeDocument) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        resume_dict = tailorer._resume_to_dict(sample_resume_document)
        assert "professional_summary" in resume_dict
        assert "experiences" in resume_dict
        assert "skills" in resume_dict
        assert isinstance(resume_dict["experiences"], list)

    def test_job_to_dict(self, sample_job_description: JobDescription) -> None:
        tailorer = JobTailorer(settings=Settings(anthropic_api_key="sk-test"))
        job_dict = tailorer._job_to_dict(sample_job_description)
        assert "title" in job_dict
        assert "company" in job_dict
        assert "required_skills" in job_dict
        assert "requirements" in job_dict


class TestKeywordMatchResult:
    """Tests for KeywordMatchResult dataclass."""

    def test_matched_property_true(self) -> None:
        result = KeywordMatchResult(
            job_keyword="Python",
            resume_keyword="Python",
            match_type="exact",
            weight=1.0,
            is_required=True,
        )
        assert result.matched is True

    def test_matched_property_false(self) -> None:
        result = KeywordMatchResult(
            job_keyword="Python",
            resume_keyword=None,
            match_type="none",
            weight=0.0,
            is_required=True,
        )
        assert result.matched is False


class TestMatchAnalysis:
    """Tests for MatchAnalysis dataclass."""

    def test_match_analysis_creation(self) -> None:
        matches = [
            KeywordMatchResult("Python", "Python", "exact", 1.0, True),
            KeywordMatchResult("AWS", None, "none", 0.0, True),
        ]
        analysis = MatchAnalysis(
            job_keywords=["Python", "AWS"],
            resume_keywords=["Python", "Docker"],
            matches=matches,
            match_rate=0.5,
            weighted_score=0.4,
            required_match_rate=0.5,
            preferred_match_rate=1.0,
            missing_required=["AWS"],
            missing_preferred=[],
            recommendations=["Add AWS"],
            meets_target=False,
        )
        assert analysis.match_rate == 0.5
        assert len(analysis.missing_required) == 1
        assert analysis.meets_target is False

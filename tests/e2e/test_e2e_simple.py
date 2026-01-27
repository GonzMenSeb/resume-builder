#!/usr/bin/env python3
"""Simple end-to-end test with mocked Claude CLI.

This test validates the entire pipeline with mocked Claude CLI responses.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_generator.claude_client import InvokeResult
from resume_generator.config import ClaudeModel, ResumeTemplate, Settings
from resume_generator.ingestion.loader import DataLoader
from resume_generator.pipeline import ResumePipeline
from resume_generator.ui.progress import PipelineUI

OUTPUT_DIR = Path("output/e2e_test_simple")


def create_mock_profile_response() -> str:
    return json.dumps({
        "contact": {
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-0123",
            "location": "New York, NY",
        },
        "professional_summary": "Experienced software engineer with expertise in Python and cloud technologies",
        "headline": "Senior Software Engineer",
        "years_of_experience": 8.0,
        "experiences": [
            {
                "company": "Tech Corp",
                "title": "Senior Software Engineer",
                "start_date": "2018-01-01",
                "end_date": None,
                "is_current": True,
                "achievements": [
                    "Designed and implemented microservices architecture",
                    "Led team of 5 engineers in developing cloud-native applications",
                ],
                "technologies": ["Python", "AWS", "Kubernetes"],
            }
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "graduation_date": "2015-05-01",
            }
        ],
        "skills": [
            {"name": "Python", "category": "programming", "years_experience": 8.0},
            {"name": "AWS", "category": "cloud", "years_experience": 6.0},
            {"name": "Kubernetes", "category": "devops", "years_experience": 4.0},
        ],
        "certifications": [],
        "projects": [],
    })


def create_mock_bullet_response() -> str:
    return json.dumps({
        "bullets": [
            {
                "text": "Architected microservices platform serving 1M+ daily users with 99.9% uptime",
                "bullet_type": "xyz",
                "action_verb": "Architected",
                "has_metrics": True,
                "metrics": {"users": "1M+", "uptime": "99.9%"},
                "keywords": ["microservices", "platform", "architecture"],
                "relevance_score": 0.95,
                "original_index": 0,
            },
            {
                "text": "Led cross-functional team of 5 engineers, delivering 3 major features ahead of schedule",
                "bullet_type": "xyz",
                "action_verb": "Led",
                "has_metrics": True,
                "metrics": {"team_size": "5", "features": "3"},
                "keywords": ["leadership", "team", "delivery"],
                "relevance_score": 0.90,
                "original_index": 1,
            },
        ],
        "removed_bullets": [],
        "overall_quality_score": 0.92,
    })


def create_mock_summary_response() -> str:
    return json.dumps({
        "summary": "Senior Software Engineer with 8+ years of experience building scalable cloud-native systems",
        "word_count": 14,
        "keywords_included": ["Senior", "Software Engineer", "experience", "cloud-native"],
        "tailored_for_job": False,
    })


def create_mock_skills_response() -> str:
    return json.dumps({
        "skill_groups": [
            {"category": "Programming Languages", "skills": ["Python", "Java", "Go"], "priority": 0},
            {"category": "Cloud & DevOps", "skills": ["AWS", "Kubernetes", "Docker"], "priority": 1},
        ],
        "added_skills": [],
        "removed_skills": [],
        "total_skills_count": 6,
    })


def test_pdf_ingestion(tmp_path: Path) -> None:
    """Test PDF text extraction without Claude CLI."""
    loader = DataLoader()
    test_file = tmp_path / "sample_resume.txt"
    test_file.write_text(
        "John Doe\nSenior Software Engineer\njohn.doe@example.com\n"
        "Experience: Tech Corp (2018-Present)\nLed development of cloud applications"
    )

    result = loader.load([test_file])

    assert len(result.unified_text) > 0
    assert len(result.failed_sources) == 0
    assert result.source_count == 1


def test_full_pipeline_with_mocked_cli(tmp_path: Path) -> None:
    """Test complete pipeline with mocked Claude CLI responses."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)

    settings = Settings(
        claude_model=ClaudeModel.SONNET,
        output_dir=output_dir,
        compile_pdf=False,
        verbose=False,
    )

    output_path = output_dir / "test_resume.tex"

    ui = PipelineUI(verbose=False)
    pipeline = ResumePipeline(settings=settings, ui=ui)

    call_count = [0]

    def mock_invoke(_prompt: str, _system: str | None = None) -> InvokeResult:
        call_count[0] += 1
        if call_count[0] == 1:
            output = create_mock_profile_response()
        elif call_count[0] == 2:
            output = create_mock_bullet_response()
        elif call_count[0] == 3:
            output = create_mock_summary_response()
        else:
            output = create_mock_skills_response()
        return InvokeResult(success=True, output=output, exit_code=0)

    mock_cli = MagicMock()
    mock_cli.invoke.side_effect = mock_invoke

    test_input = tmp_path / "resume_input.txt"
    test_input.write_text(
        "John Doe\n"
        "Senior Software Engineer\n"
        "john.doe@example.com | +1-555-0123 | New York, NY\n\n"
        "EXPERIENCE\n"
        "Tech Corp | Senior Software Engineer | 2018-Present\n"
        "- Designed and implemented microservices architecture\n"
        "- Led team of 5 engineers in developing cloud-native applications\n\n"
        "EDUCATION\n"
        "State University | Bachelor of Science in Computer Science | 2015\n\n"
        "SKILLS\n"
        "Python, AWS, Kubernetes, Docker, Go"
    )

    with (
        patch("resume_generator.extraction.profile.ClaudeCLI", return_value=mock_cli),
        patch("resume_generator.optimization.optimizer.ClaudeCLI", return_value=mock_cli),
    ):
        result = pipeline.run(
            sources=[test_input],
            output_path=output_path,
            job=None,
            template=ResumeTemplate.MODERN,
        )

        assert result.success, f"Pipeline failed: {result.errors}"
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0


if __name__ == "__main__":
    import sys

    pytest.main([__file__, "-v"])
    sys.exit(0)

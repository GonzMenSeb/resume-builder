#!/usr/bin/env python3
"""End-to-end test with real resume data from resumes/ directory."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resume_generator.claude_client import InvokeResult
from resume_generator.config import ClaudeModel, ResumeTemplate, Settings
from resume_generator.pipeline import ResumePipeline
from resume_generator.ui.progress import PipelineUI

RESUMES_DIR = Path("resumes")


def create_mock_profile_extraction_response() -> str:
    """Create mock JSON response for profile extraction."""
    return json.dumps({
        "contact": {
            "full_name": "Test User",
            "email": "test@example.com",
            "phone": "+1-555-0100",
            "location": "San Francisco, CA",
        },
        "professional_summary": "Experienced professional with strong technical skills",
        "headline": "Senior Professional",
        "years_of_experience": 5.0,
        "experiences": [
            {
                "company": "Tech Company",
                "title": "Senior Engineer",
                "start_date": "2020-01-01",
                "end_date": "2023-12-31",
                "is_current": False,
                "achievements": [
                    "Led development of key features",
                    "Improved system performance by 50%",
                ],
                "technologies": ["Python", "AWS", "Docker"],
            }
        ],
        "education": [
            {
                "institution": "University",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "graduation_date": "2016-06-01",
            }
        ],
        "skills": [
            {"name": "Python", "category": "programming", "years_experience": 5.0},
            {"name": "AWS", "category": "technical", "years_experience": 4.0},
        ],
        "certifications": [],
        "projects": [],
    })


def create_mock_bullet_batch_response() -> str:
    """Create mock JSON response for bullet optimization."""
    return json.dumps({
        "bullets": [
            {
                "text": "Led development of mission-critical features, improving system reliability by 40%",
                "bullet_type": "xyz",
                "action_verb": "Led",
                "has_metrics": True,
                "metrics": {"improvement": "40%"},
                "keywords": ["development", "features", "system", "reliability"],
                "relevance_score": 0.9,
                "original_index": 0,
            },
            {
                "text": "Optimized infrastructure reducing costs by $50K annually",
                "bullet_type": "xyz",
                "action_verb": "Optimized",
                "has_metrics": True,
                "metrics": {"savings": "$50K"},
                "keywords": ["infrastructure", "optimization", "costs"],
                "relevance_score": 0.85,
                "original_index": 1,
            },
        ],
        "removed_bullets": [],
        "overall_quality_score": 0.87,
    })


def create_mock_professional_summary_response() -> str:
    """Create mock JSON response for professional summary."""
    return json.dumps({
        "summary": "Results-driven professional with 5+ years of experience delivering high-impact solutions",
        "word_count": 12,
        "keywords_included": ["professional", "experience", "solutions"],
        "tailored_for_job": False,
    })


def create_mock_skills_optimization_response() -> str:
    """Create mock JSON response for skills optimization."""
    return json.dumps({
        "skill_groups": [
            {"category": "Languages", "skills": ["Python", "JavaScript", "Go"], "priority": 0},
            {"category": "Cloud & DevOps", "skills": ["AWS", "Docker", "Kubernetes"], "priority": 1},
        ],
        "added_skills": [],
        "removed_skills": [],
        "total_skills_count": 6,
    })


@pytest.mark.skipif(not RESUMES_DIR.exists(), reason="resumes/ directory not found")
@pytest.mark.parametrize("pdf_file", list(RESUMES_DIR.glob("*.pdf")) if RESUMES_DIR.exists() else [])
def test_e2e_with_real_pdf(pdf_file: Path, tmp_path: Path) -> None:
    """Test the entire pipeline with real PDF files from resumes/ directory.

    This test uses mocked Claude CLI responses to avoid requiring API access
    while still validating the full pipeline with real PDF ingestion.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)

    settings = Settings(
        claude_model=ClaudeModel.SONNET,
        output_dir=output_dir,
        compile_pdf=False,
        verbose=False,
    )

    output_name = pdf_file.stem + "_generated"
    output_path = output_dir / f"{output_name}.tex"

    ui = PipelineUI(verbose=False)
    pipeline = ResumePipeline(settings=settings, ui=ui)

    call_count = [0]

    def mock_invoke(_prompt: str, _system: str | None = None) -> InvokeResult:
        call_count[0] += 1
        if call_count[0] == 1:
            output = create_mock_profile_extraction_response()
        elif call_count[0] == 2:
            output = create_mock_bullet_batch_response()
        elif call_count[0] == 3:
            output = create_mock_professional_summary_response()
        else:
            output = create_mock_skills_optimization_response()
        return InvokeResult(success=True, output=output, exit_code=0)

    mock_cli = MagicMock()
    mock_cli.invoke.side_effect = mock_invoke

    with (
        patch("resume_generator.extraction.profile.ClaudeCLI", return_value=mock_cli),
        patch("resume_generator.optimization.optimizer.ClaudeCLI", return_value=mock_cli),
    ):
        result = pipeline.run(
            sources=[pdf_file],
            output_path=output_path,
            job=None,
            template=ResumeTemplate.MODERN,
        )

        assert result.success, f"Pipeline failed for {pdf_file.name}: {result.errors}"
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0, "Output file is empty"


if __name__ == "__main__":
    import sys

    pytest.main([__file__, "-v"])
    sys.exit(0)

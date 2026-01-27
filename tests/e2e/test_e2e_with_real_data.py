#!/usr/bin/env python3
"""End-to-end test with real resume data from resumes/ directory."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from resume_generator.claude_client import InvokeResult
from resume_generator.config import ClaudeModel, ResumeTemplate, Settings
from resume_generator.pipeline import ResumePipeline
from resume_generator.ui.progress import PipelineUI

RESUMES_DIR = Path("resumes")
OUTPUT_DIR = Path("output/e2e_test")


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


def test_e2e_with_real_pdfs():
    """Test the entire pipeline with real PDF files from resumes/ directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(RESUMES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {RESUMES_DIR}")
        return False

    print(f"📁 Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"  • {pdf.name}")

    settings = Settings(
        claude_model=ClaudeModel.SONNET,
        output_dir=OUTPUT_DIR,
        compile_pdf=False,
        verbose=True,
    )

    all_success = True

    for pdf_file in pdf_files:
        print(f"\n{'=' * 60}")
        print(f"Testing with: {pdf_file.name}")
        print(f"{'=' * 60}\n")

        output_name = pdf_file.stem + "_generated"
        output_path = OUTPUT_DIR / f"{output_name}.tex"

        ui = PipelineUI(verbose=True)
        pipeline = ResumePipeline(settings=settings, ui=ui)

        call_count = [0]

        def mock_invoke(prompt: str, system: str | None = None) -> InvokeResult:
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
            patch(
                "resume_generator.extraction.profile.ClaudeCLI",
                return_value=mock_cli,
            ),
            patch(
                "resume_generator.optimization.optimizer.ClaudeCLI",
                return_value=mock_cli,
            ),
        ):
            try:
                result = pipeline.run(
                    sources=[pdf_file],
                    output_path=output_path,
                    job=None,
                    template=ResumeTemplate.MODERN,
                )

                if result.success:
                    print(f"\n✅ Successfully processed {pdf_file.name}")
                    print(f"   Output: {result.output_path}")

                    if result.output_path and result.output_path.exists():
                        file_size = result.output_path.stat().st_size
                        print(f"   Size: {file_size} bytes")

                        if file_size == 0:
                            print("   ⚠️  Warning: Output file is empty")
                            all_success = False
                    else:
                        print(f"   ⚠️  Warning: Output file not found at {result.output_path}")
                        all_success = False
                else:
                    print(f"\n❌ Failed to process {pdf_file.name}")
                    for error in result.errors:
                        print(f"   Error: {error}")
                    all_success = False

            except Exception as e:
                print(f"\n❌ Exception while processing {pdf_file.name}: {e}")
                import traceback

                traceback.print_exc()
                all_success = False

    print(f"\n{'=' * 60}")
    if all_success:
        print("✅ All end-to-end tests PASSED")
    else:
        print("❌ Some end-to-end tests FAILED")
    print(f"{'=' * 60}\n")

    return all_success


if __name__ == "__main__":
    import sys

    success = test_e2e_with_real_pdfs()
    sys.exit(0 if success else 1)

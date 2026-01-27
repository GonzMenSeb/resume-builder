#!/usr/bin/env python3
"""End-to-end test with real resume data from resumes/ directory."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import date
from resume_generator.config import Settings, ClaudeModel, ResumeTemplate
from resume_generator.pipeline import ResumePipeline
from resume_generator.ui.progress import PipelineUI

RESUMES_DIR = Path("resumes")
OUTPUT_DIR = Path("output/e2e_test")


def create_mock_profile_extraction_schema():
    """Create mock ProfileExtractionSchema for mocking."""
    from resume_generator.extraction.profile import (
        ProfileExtractionSchema,
        ContactInfoSchema,
        ExperienceSchema,
        EducationSchema,
        SkillSchema,
    )

    return ProfileExtractionSchema(
        contact=ContactInfoSchema(
            full_name="Test User",
            email="test@example.com",
            phone="+1-555-0100",
            location="San Francisco, CA"
        ),
        professional_summary="Experienced professional with strong technical skills",
        headline="Senior Professional",
        years_of_experience=5.0,
        experiences=[
            ExperienceSchema(
                company="Tech Company",
                title="Senior Engineer",
                start_date="2020-01-01",
                end_date="2023-12-31",
                is_current=False,
                achievements=[
                    "Led development of key features",
                    "Improved system performance by 50%"
                ],
                technologies=["Python", "AWS", "Docker"]
            )
        ],
        education=[
            EducationSchema(
                institution="University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                graduation_date="2016-06-01"
            )
        ],
        skills=[
            SkillSchema(name="Python", category="programming", years_experience=5.0),
            SkillSchema(name="AWS", category="technical", years_experience=4.0)
        ]
    )


def create_mock_resume_optimization_schema():
    """Create mock ResumeOptimizationSchema for mocking."""
    from resume_generator.optimization.optimizer import (
        ResumeOptimizationSchema,
        OptimizedExperienceSchema,
        BulletSchema,
        SkillGroupSchema,
        EducationOutputSchema,
    )

    return ResumeOptimizationSchema(
        professional_summary="Results-driven professional with 5+ years of experience delivering high-impact solutions",
        experiences=[
            OptimizedExperienceSchema(
                company="Tech Company",
                title="Senior Engineer",
                start_date="2020-01-01",
                end_date="2023-12-31",
                is_current=False,
                bullets=[
                    BulletSchema(
                        text="Led development of mission-critical features, improving system reliability by 40%",
                        bullet_type="xyz",
                        action_verb="Led",
                        metrics={"improvement": "40%"},
                        keywords=["development", "features", "system", "reliability"]
                    ),
                    BulletSchema(
                        text="Optimized infrastructure reducing costs by $50K annually",
                        bullet_type="xyz",
                        action_verb="Optimized",
                        metrics={"savings": "$50K"},
                        keywords=["infrastructure", "optimization", "costs"]
                    )
                ]
            )
        ],
        skills=[
            SkillGroupSchema(category="Languages", skills=["Python", "JavaScript", "Go"]),
            SkillGroupSchema(category="Cloud & DevOps", skills=["AWS", "Docker", "Kubernetes"])
        ],
        education=[
            EducationOutputSchema(
                institution="University",
                degree="B.S. in Computer Science",
                graduation_date="2016-06-01",
                honors=[]
            )
        ]
    )


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
        anthropic_api_key="sk-ant-test-key-e2e",
        claude_model=ClaudeModel.SONNET,
        output_dir=OUTPUT_DIR,
        compile_pdf=False,
        verbose=True,
    )

    all_success = True

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Testing with: {pdf_file.name}")
        print(f"{'='*60}\n")

        output_name = pdf_file.stem + "_generated"
        output_path = OUTPUT_DIR / f"{output_name}.tex"

        ui = PipelineUI(verbose=True)
        pipeline = ResumePipeline(settings=settings, ui=ui)

        with patch("resume_generator.extraction.profile.Anthropic") as mock_anthropic_extract, \
             patch("resume_generator.optimization.optimizer.Anthropic") as mock_anthropic_opt:

            mock_extract_client = MagicMock()
            mock_opt_client = MagicMock()

            mock_extract_response = MagicMock()
            mock_extract_response.stop_reason = "end_turn"
            mock_extract_response.parsed_output = create_mock_profile_extraction_schema()
            mock_extract_client.beta.messages.parse.return_value = mock_extract_response

            mock_opt_response = MagicMock()
            mock_opt_response.stop_reason = "end_turn"
            mock_opt_response.parsed_output = create_mock_resume_optimization_schema()
            mock_opt_client.beta.messages.parse.return_value = mock_opt_response

            mock_anthropic_extract.return_value = mock_extract_client
            mock_anthropic_opt.return_value = mock_opt_client

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
                            print(f"   ⚠️  Warning: Output file is empty")
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

    print(f"\n{'='*60}")
    if all_success:
        print("✅ All end-to-end tests PASSED")
    else:
        print("❌ Some end-to-end tests FAILED")
    print(f"{'='*60}\n")

    return all_success


if __name__ == "__main__":
    import sys
    success = test_e2e_with_real_pdfs()
    sys.exit(0 if success else 1)

"""Pytest fixtures for resume generator tests."""

import json
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import Message, TextBlock, Usage

from resume_generator.config import ClaudeModel, Settings
from resume_generator.models.job import (
    EmploymentType,
    ExperienceLevel,
    JobDescription,
    JobRequirement,
    RequirementPriority,
    WorkArrangement,
)
from resume_generator.models.profile import (
    Certification,
    ContactInfo,
    Education,
    Experience,
    PersonProfile,
    Project,
    Skill,
    SkillCategory,
)
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


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Temporary directory for test files."""
    return tmp_path


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Temporary output directory."""
    out_dir = tmp_path / "output"
    out_dir.mkdir(exist_ok=True)
    return out_dir


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir(exist_ok=True)
    return cache


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Test settings with temporary directories and fake API key."""
    return Settings(
        anthropic_api_key="sk-ant-test-key-12345",
        claude_model=ClaudeModel.SONNET,
        output_dir=tmp_path / "output",
        cache_dir=tmp_path / "cache",
        templates_dir=Path(__file__).parent.parent
        / "src"
        / "resume_generator"
        / "generation"
        / "templates",
        max_tokens=2048,
        api_timeout=30.0,
        api_max_retries=2,
        verbose=False,
        compile_pdf=False,
    )


@pytest.fixture
def sample_contact_info() -> ContactInfo:
    """Sample contact information."""
    return ContactInfo(
        full_name="Jane Doe",
        email="jane.doe@example.com",
        phone="+1-555-0123",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/janedoe",
        github_url="https://github.com/janedoe",
        portfolio_url="https://janedoe.dev",
    )


@pytest.fixture
def sample_skill() -> Skill:
    """Sample skill entry."""
    return Skill(
        name="Python",
        category=SkillCategory.PROGRAMMING,
        proficiency=5,
        years_experience=5.0,
        keywords=["python", "python3", "programming"],
    )


@pytest.fixture
def sample_experience() -> Experience:
    """Sample work experience entry."""
    return Experience(
        company="Tech Corp",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        start_date=date(2020, 1, 1),
        end_date=date(2023, 6, 30),
        is_current=False,
        description="Led development of cloud infrastructure",
        achievements=[
            "Reduced deployment time by 60% through CI/CD automation",
            "Architected microservices platform handling 10M+ requests/day",
            "Mentored team of 5 junior engineers",
        ],
        technologies=["Python", "AWS", "Docker", "Kubernetes"],
        metrics={"deployment_reduction": "60%", "requests_daily": "10M+"},
    )


@pytest.fixture
def sample_education() -> Education:
    """Sample education entry."""
    return Education(
        institution="Stanford University",
        degree="Bachelor of Science",
        field_of_study="Computer Science",
        location="Stanford, CA",
        start_date=date(2012, 9, 1),
        graduation_date=date(2016, 6, 15),
        gpa=3.8,
        honors=["Cum Laude", "Dean's List"],
        relevant_coursework=["Algorithms", "Machine Learning", "Systems Design"],
    )


@pytest.fixture
def sample_certification() -> Certification:
    """Sample certification entry."""
    return Certification(
        name="AWS Certified Solutions Architect",
        acronym="AWS-SAA",
        issuing_organization="Amazon Web Services",
        date_earned=date(2021, 3, 15),
        credential_id="AWS-1234567890",
        url="https://aws.amazon.com/verification/1234567890",
    )


@pytest.fixture
def sample_project() -> Project:
    """Sample project entry."""
    return Project(
        name="Open Source ML Framework",
        description="Distributed machine learning framework for edge devices",
        role="Core Maintainer",
        url="https://github.com/example/ml-framework",
        repository_url="https://github.com/example/ml-framework",
        start_date=date(2022, 1, 1),
        technologies=["Python", "TensorFlow", "PyTorch", "C++"],
        highlights=[
            "10K+ GitHub stars",
            "Used by 50+ companies in production",
            "Reduced inference time by 3x on edge devices",
        ],
    )


@pytest.fixture
def sample_person_profile(
    sample_contact_info: ContactInfo,
    sample_skill: Skill,
    sample_experience: Experience,
    sample_education: Education,
    sample_certification: Certification,
    sample_project: Project,
) -> PersonProfile:
    """Complete sample person profile."""
    return PersonProfile(
        contact=sample_contact_info,
        professional_summary="Experienced software engineer with 5+ years building scalable cloud infrastructure and leading high-performing teams. Specialized in Python, AWS, and DevOps.",
        headline="Senior Software Engineer | Cloud Architecture | DevOps",
        years_of_experience=5.0,
        experiences=[sample_experience],
        education=[sample_education],
        skills=[
            sample_skill,
            Skill(name="AWS", category=SkillCategory.TECHNICAL, years_experience=4.0),
            Skill(name="Docker", category=SkillCategory.TOOLS, years_experience=4.0),
            Skill(name="Kubernetes", category=SkillCategory.TOOLS, years_experience=3.0),
        ],
        certifications=[sample_certification],
        projects=[sample_project],
        awards=["Employee of the Year 2022"],
        languages=[("English", "Native"), ("Spanish", "Professional")],
    )


@pytest.fixture
def sample_resume_bullet() -> ResumeBullet:
    """Sample optimized resume bullet."""
    return ResumeBullet(
        text="Engineered automated CI/CD pipeline reducing deployment time from 4 hours to 90 minutes (60% reduction) using Jenkins, Docker, and AWS CodeDeploy",
        bullet_type=BulletType.XYZ,
        action_verb="Engineered",
        metrics={"time_reduction": "60%", "from": "4 hours", "to": "90 minutes"},
        keywords=["CI/CD", "Jenkins", "Docker", "AWS", "automation"],
        relevance_score=0.95,
    )


@pytest.fixture
def sample_resume_experience(sample_resume_bullet: ResumeBullet) -> ResumeExperience:
    """Sample resume experience entry."""
    return ResumeExperience(
        company="Tech Corp",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        start_date=date(2020, 1, 1),
        end_date=date(2023, 6, 30),
        is_current=False,
        bullets=[
            sample_resume_bullet,
            ResumeBullet(
                text="Architected microservices platform processing 10M+ daily requests with 99.9% uptime using Python, FastAPI, and Kubernetes",
                bullet_type=BulletType.ACTION_RESULT,
                action_verb="Architected",
                metrics={"requests": "10M+", "uptime": "99.9%"},
                keywords=["microservices", "Python", "FastAPI", "Kubernetes"],
                relevance_score=0.90,
            ),
            ResumeBullet(
                text="Mentored team of 5 junior engineers, improving code quality scores by 40% through code reviews and pair programming",
                bullet_type=BulletType.XYZ,
                action_verb="Mentored",
                metrics={"team_size": "5", "improvement": "40%"},
                keywords=["mentorship", "leadership", "code review"],
                relevance_score=0.75,
            ),
        ],
        technologies=["Python", "AWS", "Docker", "Kubernetes", "FastAPI"],
    )


@pytest.fixture
def sample_resume_contact(sample_contact_info: ContactInfo) -> ResumeContact:
    """Sample resume contact info."""
    return ResumeContact(
        name=sample_contact_info.full_name,
        email=str(sample_contact_info.email),
        phone=sample_contact_info.phone,
        location=sample_contact_info.location,
        linkedin_url=sample_contact_info.linkedin_url,
        github_url=sample_contact_info.github_url,
        portfolio_url=sample_contact_info.portfolio_url,
    )


@pytest.fixture
def sample_resume_document(
    sample_resume_contact: ResumeContact,
    sample_resume_experience: ResumeExperience,
) -> ResumeDocument:
    """Complete sample resume document."""
    return ResumeDocument(
        contact=sample_resume_contact,
        professional_summary="Results-driven Senior Software Engineer with 5+ years of experience designing and implementing scalable cloud infrastructure. Proven track record of reducing deployment times by 60% and architecting systems handling 10M+ daily requests. Expert in Python, AWS, and DevOps practices.",
        headline="Senior Software Engineer | Cloud Architecture | DevOps",
        experiences=[sample_resume_experience],
        education=[
            ResumeEducation(
                institution="Stanford University",
                degree="B.S. in Computer Science",
                location="Stanford, CA",
                graduation_date=date(2016, 6, 15),
                gpa="3.8/4.0",
                honors=["Cum Laude", "Dean's List"],
            )
        ],
        skills=[
            ResumeSkillGroup(
                category="Languages",
                skills=["Python", "Go", "JavaScript", "SQL"],
            ),
            ResumeSkillGroup(
                category="Cloud & DevOps",
                skills=["AWS", "Docker", "Kubernetes", "Terraform", "Jenkins"],
            ),
            ResumeSkillGroup(
                category="Frameworks",
                skills=["FastAPI", "Django", "React", "PostgreSQL"],
            ),
        ],
        certifications=[
            ResumeCertification(
                name="AWS Certified Solutions Architect",
                issuer="Amazon Web Services",
                date_earned=date(2021, 3, 15),
            )
        ],
        projects=[
            ResumeProject(
                name="Open Source ML Framework",
                url="https://github.com/example/ml-framework",
                description="Distributed ML framework for edge devices",
                technologies=["Python", "TensorFlow", "C++"],
                highlights=["10K+ GitHub stars", "Used by 50+ companies"],
            )
        ],
        target_job_title="Senior Software Engineer",
        keyword_match_rate=0.78,
        optimization_score=0.85,
    )


@pytest.fixture
def sample_job_requirement() -> JobRequirement:
    """Sample job requirement."""
    return JobRequirement(
        text="5+ years of experience with Python and cloud infrastructure",
        priority=RequirementPriority.REQUIRED,
        category="experience",
        keywords=["Python", "cloud", "infrastructure", "AWS"],
        years_experience=5,
    )


@pytest.fixture
def sample_job_description(sample_job_requirement: JobRequirement) -> JobDescription:
    """Complete sample job description."""
    return JobDescription(
        title="Senior Software Engineer",
        company="Tech Innovations Inc",
        location="San Francisco, CA",
        work_arrangement=WorkArrangement.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        experience_level=ExperienceLevel.SENIOR,
        department="Engineering",
        description="We are seeking a talented Senior Software Engineer to join our cloud infrastructure team.",
        responsibilities=[
            "Design and implement scalable cloud infrastructure",
            "Lead technical initiatives and mentor junior engineers",
            "Collaborate with cross-functional teams",
        ],
        requirements=[
            sample_job_requirement,
            JobRequirement(
                text="Experience with containerization (Docker, Kubernetes)",
                priority=RequirementPriority.REQUIRED,
                category="technical",
                keywords=["Docker", "Kubernetes", "containers"],
            ),
            JobRequirement(
                text="Familiarity with CI/CD pipelines",
                priority=RequirementPriority.PREFERRED,
                category="technical",
                keywords=["CI/CD", "Jenkins", "automation"],
            ),
        ],
        required_skills=["Python", "AWS", "Docker", "Kubernetes", "CI/CD"],
        preferred_skills=["Go", "Terraform", "PostgreSQL"],
        required_education="Bachelor's degree in Computer Science or related field",
        min_years_experience=5,
        max_years_experience=10,
        posting_url="https://example.com/jobs/senior-engineer",
        raw_text="Senior Software Engineer job posting...",
    )


@pytest.fixture
def sample_raw_text() -> str:
    """Sample raw text for profile extraction."""
    return """
JOHN DOE
john.doe@email.com | (555) 123-4567 | San Francisco, CA
LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

PROFESSIONAL SUMMARY
Software engineer with 6 years of experience in full-stack development.
Specialized in Python, React, and cloud technologies.

WORK EXPERIENCE

Senior Developer | Acme Corp | Jan 2021 - Present
- Built microservices handling 5M requests per day
- Reduced API response time by 45%
- Led team of 3 developers

Software Engineer | StartupXYZ | Jun 2018 - Dec 2020
- Developed React frontend for e-commerce platform
- Implemented payment processing with Stripe
- Improved test coverage from 40% to 85%

EDUCATION
B.S. Computer Science | MIT | 2018
GPA: 3.7 | Dean's List

SKILLS
Python, JavaScript, React, Node.js, AWS, Docker, PostgreSQL
"""


@pytest.fixture
def sample_pdf_content(tmp_path: Path) -> Path:
    """Create a sample text file simulating extracted PDF content."""
    pdf_file = tmp_path / "sample_resume.txt"
    pdf_file.write_text(
        "Jane Smith\nSoftware Engineer\njane@example.com\n\n"
        "Experience: 5 years in Python and cloud development\n"
        "Skills: Python, AWS, Docker, Kubernetes\n"
    )
    return pdf_file


@pytest.fixture
def sample_markdown_file(tmp_path: Path) -> Path:
    """Create a sample markdown file."""
    md_file = tmp_path / "profile.md"
    md_file.write_text(
        "# John Developer\n\n"
        "## Contact\n"
        "- Email: john@example.com\n"
        "- Phone: 555-0100\n\n"
        "## Experience\n"
        "**Software Engineer** at Tech Co (2019-2023)\n"
        "- Built scalable APIs\n"
        "- Reduced latency by 50%\n"
    )
    return md_file


@pytest.fixture
def mock_claude_response() -> Message:
    """Mock Claude API response."""
    return Message(
        id="msg_test123",
        type="message",
        role="assistant",
        content=[
            TextBlock(
                type="text",
                text='{"full_name": "Jane Doe", "email": "jane@example.com"}',
            )
        ],
        model="claude-sonnet-4-20250514",
        stop_reason="end_turn",
        usage=Usage(input_tokens=100, output_tokens=50),
    )


@pytest.fixture
def mock_claude_client(mock_claude_response: Message) -> MagicMock:
    """Mock Anthropic client."""
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=mock_claude_response)
    return client


@pytest.fixture
def mock_profile_extraction_response() -> dict[str, Any]:
    """Mock response for profile extraction."""
    return {
        "contact": {
            "full_name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "+1-555-0123",
            "location": "San Francisco, CA",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "github_url": "https://github.com/janedoe",
        },
        "professional_summary": "Experienced software engineer with 5+ years in cloud development",
        "headline": "Senior Software Engineer",
        "years_of_experience": 5.0,
        "experiences": [
            {
                "company": "Tech Corp",
                "title": "Senior Software Engineer",
                "start_date": "2020-01-01",
                "end_date": "2023-06-30",
                "achievements": ["Reduced deployment time by 60%"],
                "technologies": ["Python", "AWS"],
            }
        ],
        "education": [
            {
                "institution": "Stanford University",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "graduation_date": "2016-06-15",
            }
        ],
        "skills": [
            {"name": "Python", "category": "programming"},
            {"name": "AWS", "category": "technical"},
        ],
    }


@pytest.fixture
def mock_optimization_response() -> str:
    """Mock response for resume optimization."""
    return json.dumps(
        {
            "professional_summary": "Results-driven Senior Software Engineer with 5+ years of experience designing and implementing scalable cloud infrastructure.",
            "experiences": [
                {
                    "company": "Tech Corp",
                    "title": "Senior Software Engineer",
                    "bullets": [
                        {
                            "text": "Engineered automated CI/CD pipeline reducing deployment time by 60%",
                            "type": "xyz",
                            "action_verb": "Engineered",
                            "metrics": {"reduction": "60%"},
                        }
                    ],
                }
            ],
        }
    )


@pytest.fixture
def sample_latex_template(tmp_path: Path) -> Path:
    """Create a minimal sample LaTeX template."""
    template = tmp_path / "test_template.tex"
    template.write_text(
        r"""\documentclass{article}
\begin{document}
\section*{{{ contact.name }}}
{{ contact.email }}

{% if professional_summary %}
\section*{Summary}
{{ professional_summary }}
{% endif %}

\end{document}
"""
    )
    return template


@pytest.fixture
def env_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set environment variable for API key."""
    monkeypatch.setenv("RESUME_GEN_ANTHROPIC_API_KEY", "sk-ant-test-key-12345")


@pytest.fixture
def multiple_input_files(tmp_path: Path) -> list[Path]:
    """Create multiple input files for testing data loader."""
    files = []

    txt_file = tmp_path / "resume.txt"
    txt_file.write_text("Name: Alice Engineer\nSkills: Python, Docker, AWS")
    files.append(txt_file)

    md_file = tmp_path / "experience.md"
    md_file.write_text("# Work History\n\n## Software Engineer\nWorked on distributed systems")
    files.append(md_file)

    return files

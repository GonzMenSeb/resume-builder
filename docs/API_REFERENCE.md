# API Reference

## Overview

The Resume Generator provides a Python API for programmatic resume generation. This reference documents all public classes, methods, and data models.

## Installation

```bash
pip install resume-generator
```

## Quick Start

```python
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.config import get_settings

settings = get_settings()
pipeline = ResumePipeline(settings=settings)

result = pipeline.run(
    sources=[Path("resume.pdf")],
    output_path=Path("output/resume.pdf")
)

print(f"Generated: {result.output_path}")
```

## Core Classes

### ResumePipeline

Main orchestrator for the resume generation pipeline.

**Constructor:**
```python
ResumePipeline(
    settings: Settings | None = None,
    ui: PipelineUI | None = None
)
```

**Parameters:**
- `settings`: Configuration settings (uses defaults if None)
- `ui`: Progress UI instance (None disables UI)

#### Methods

##### `run()`

Execute the full pipeline synchronously.

```python
def run(
    sources: Path | str | Sequence[Path | str],
    output_path: Path | None = None,
    job: JobDescription | None = None,
    template: ResumeTemplate | None = None,
) -> PipelineResult
```

**Parameters:**
- `sources`: Input files, directories, or text
- `output_path`: Destination path for output (auto-generated if None)
- `job`: Job description for tailoring (None skips tailoring)
- `template`: Template choice (uses default if None)

**Returns:** `PipelineResult` object

**Raises:** `PipelineError` if any stage fails

**Example:**
```python
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.models.job import JobDescription

pipeline = ResumePipeline()

result = pipeline.run(
    sources=[Path("resume.pdf"), Path("experience.md")],
    output_path=Path("output/my_resume.pdf"),
    job=JobDescription(
        title="Senior Python Developer",
        raw_text="We're looking for a Python expert with..."
    )
)

if result.success:
    print(f"✓ Resume generated: {result.output_path}")
    print(f"  Optimization score: {result.optimization_score:.2f}")
    print(f"  Keyword match: {result.keyword_match_rate:.0%}")
```

##### `run_async()`

Execute the pipeline asynchronously.

```python
async def run_async(
    sources: Path | str | Sequence[Path | str],
    output_path: Path | None = None,
    job: JobDescription | None = None,
    template: ResumeTemplate | None = None,
) -> PipelineResult
```

**Parameters:** Same as `run()`

**Returns:** `PipelineResult` (awaitable)

**Example:**
```python
import asyncio
from resume_generator import ResumePipeline

async def generate():
    pipeline = ResumePipeline()
    result = await pipeline.run_async(
        sources=["resume.pdf"],
        output_path="output/resume.pdf"
    )
    return result

result = asyncio.run(generate())
```

##### `run_with_callbacks()`

Execute pipeline with custom stage callbacks.

```python
def run_with_callbacks(
    sources: Path | str | Sequence[Path | str],
    output_path: Path | None = None,
    job: JobDescription | None = None,
    template: ResumeTemplate | None = None,
    on_stage_start: Callable[[PipelineStage], None] | None = None,
    on_stage_complete: Callable[[PipelineStage, StageResult], None] | None = None,
    on_error: Callable[[PipelineStage, Exception], None] | None = None,
) -> PipelineResult
```

**Callback Parameters:**
- `on_stage_start(stage)`: Called when stage begins
- `on_stage_complete(stage, result)`: Called when stage succeeds
- `on_error(stage, exception)`: Called when stage fails

**Example:**
```python
from resume_generator import ResumePipeline
from resume_generator.ui.progress import PipelineStage

def on_complete(stage: PipelineStage, result):
    print(f"✓ {stage.value} completed in {result.duration_seconds:.2f}s")

pipeline = ResumePipeline()
result = pipeline.run_with_callbacks(
    sources=["resume.pdf"],
    on_stage_complete=on_complete
)
```

### PipelineResult

Result object returned by pipeline execution.

**Attributes:**

```python
@dataclass
class PipelineResult:
    success: bool
    pdf_path: Path | None
    tex_path: Path | None
    resume: ResumeDocument | None
    profile: PersonProfile | None
    load_result: LoadResult | None
    compilation_result: CompilationResult | None
    keyword_match_rate: float
    optimization_score: float
    errors: list[str]
    stage_results: list[StageResult]
    total_duration_seconds: float
```

**Properties:**

- `output_path`: Returns `pdf_path` or `tex_path`
- `completed_stages`: List of successfully completed stages
- `failed_stage`: First stage that failed (None if all succeeded)

**Example:**
```python
result = pipeline.run(sources=["resume.pdf"])

if result.success:
    print(f"Output: {result.output_path}")
    print(f"Stages completed: {len(result.completed_stages)}")
    print(f"Total time: {result.total_duration_seconds:.1f}s")

    if result.resume:
        print(f"Bullets: {result.resume.total_bullet_count}")
        print(f"Score: {result.optimization_score:.2f}")
else:
    print(f"Failed at: {result.failed_stage}")
    for error in result.errors:
        print(f"Error: {error}")
```

### Settings

Configuration management using Pydantic Settings.

```python
from resume_generator.config import Settings, ClaudeModel, get_settings
from pathlib import Path

settings = get_settings()

settings.claude_model = ClaudeModel.SONNET
settings.claude_cli_timeout = 3600
settings.output_dir = Path("./output")
settings.compile_pdf = True
```

**Key Settings:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `claude_model` | ClaudeModel | `SONNET` | Claude model to use |
| `claude_cli_timeout` | int | `3600` | Claude CLI timeout (seconds) |
| `claude_cli_verbose` | bool | `False` | Verbose Claude CLI output |
| `output_dir` | Path | `./output` | Output directory |
| `default_template` | ResumeTemplate | `MODERN` | Default template |
| `compile_pdf` | bool | `True` | Enable PDF compilation |
| `enable_job_tailoring` | bool | `True` | Enable job tailoring |
| `verbose` | bool | `False` | Verbose logging |

See [CONFIGURATION.md](./CONFIGURATION.md) for complete reference.

## Data Models

### PersonProfile

Raw profile data extracted from source materials.

```python
from resume_generator.models.profile import PersonProfile, WorkExperience, Education

profile = PersonProfile(
    name="John Doe",
    email="john@example.com",
    phone="+1-555-0100",
    location="San Francisco, CA",
    experiences=[
        WorkExperience(
            company="Tech Corp",
            role="Senior Developer",
            start_date="2020-01",
            end_date="present",
            bullets=[
                "Built scalable APIs",
                "Led team of 5 engineers"
            ]
        )
    ],
    education=[
        Education(
            institution="University",
            degree="BS Computer Science",
            graduation_year="2019"
        )
    ],
    skills=["Python", "Django", "PostgreSQL"]
)
```

**Key Attributes:**

- `name: str`: Full name
- `email: str | None`: Email address
- `phone: str | None`: Phone number
- `location: str | None`: Location/address
- `linkedin: str | None`: LinkedIn URL
- `github: str | None`: GitHub URL
- `website: str | None`: Personal website
- `summary: str | None`: Professional summary
- `experiences: list[WorkExperience]`: Work history
- `education: list[Education]`: Education background
- `skills: list[str]`: Technical skills
- `certifications: list[str]`: Certifications
- `projects: list[Project]`: Personal projects

### ResumeDocument

Optimized resume content ready for generation.

```python
from resume_generator.models.resume import ResumeDocument, ContactInfo

resume = ResumeDocument(
    contact=ContactInfo(
        name="John Doe",
        email="john@example.com",
        phone="+1-555-0100"
    ),
    summary="Experienced Python developer...",
    experiences=[...],
    education=[...],
    skills=["Python", "Django"],
    optimization_score=0.85,
    keyword_match_rate=0.72
)
```

**Key Attributes:**

- `contact: ContactInfo`: Contact information
- `summary: str | None`: Professional summary
- `experiences: list[WorkExperience]`: Optimized work history
- `education: list[Education]`: Education entries
- `skills: list[str]`: Skill list
- `certifications: list[str]`: Certifications
- `projects: list[Project]`: Projects
- `target_job_title: str | None`: Job being targeted
- `optimization_score: float | None`: Optimization quality (0-1)
- `keyword_match_rate: float | None`: Keyword match rate (0-1)

**Properties:**

- `total_bullet_count`: Total bullet points across all experiences

### JobDescription

Job posting information for tailoring.

```python
from resume_generator.models.job import JobDescription

job = JobDescription(
    title="Senior Python Developer",
    company="Tech Startup",
    raw_text="""
    We're seeking a Senior Python Developer with 5+ years experience.
    Requirements: Python, Django, PostgreSQL, AWS, Docker.
    """
)

keywords = job.get_keyword_set()  # Extracted keywords
```

**Attributes:**

- `title: str`: Job title
- `company: str | None`: Company name
- `raw_text: str`: Full job description text
- `url: str | None`: Job posting URL

**Methods:**

- `get_keyword_set() -> set[str]`: Extract keywords from job description

### WorkExperience

Work experience entry.

```python
from resume_generator.models.profile import WorkExperience

exp = WorkExperience(
    company="Tech Corp",
    role="Senior Engineer",
    start_date="2020-01",
    end_date="present",
    location="San Francisco, CA",
    bullets=[
        "Built microservices handling 1M+ requests/day",
        "Led team of 5 engineers"
    ]
)
```

**Attributes:**

- `company: str`: Company name
- `role: str`: Job title/role
- `start_date: str`: Start date (YYYY-MM format)
- `end_date: str | None`: End date or "present"
- `location: str | None`: Job location
- `bullets: list[str]`: Achievement bullet points

### Education

Education background.

```python
from resume_generator.models.profile import Education

edu = Education(
    institution="Stanford University",
    degree="MS Computer Science",
    field="Machine Learning",
    graduation_year="2020",
    gpa="3.9",
    honors=["Summa Cum Laude"]
)
```

**Attributes:**

- `institution: str`: School/university name
- `degree: str`: Degree type (BS, MS, PhD, etc.)
- `field: str | None`: Field of study
- `graduation_year: str | None`: Graduation year
- `gpa: str | None`: GPA
- `honors: list[str]`: Honors and awards

### Enums

#### ResumeTemplate

```python
from resume_generator.config import ResumeTemplate

template = ResumeTemplate.MODERN  # Professional modern design
template = ResumeTemplate.ATS     # ATS-friendly format
```

#### PipelineStage

```python
from resume_generator.ui.progress import PipelineStage

stage = PipelineStage.LOADING
stage = PipelineStage.EXTRACTING
stage = PipelineStage.OPTIMIZING
stage = PipelineStage.TAILORING
stage = PipelineStage.GENERATING
stage = PipelineStage.COMPILING
```

#### StageStatus

```python
from resume_generator.pipeline import StageStatus

status = StageStatus.PENDING
status = StageStatus.RUNNING
status = StageStatus.COMPLETED
status = StageStatus.FAILED
status = StageStatus.SKIPPED
```

## Exceptions

### PipelineError

Base exception for all pipeline errors.

```python
from resume_generator.pipeline import PipelineError

try:
    result = pipeline.run(sources=["resume.pdf"])
except PipelineError as e:
    print(f"Pipeline failed: {e}")
    print(f"Stage: {e.stage}")
    print(f"Cause: {e.cause}")
```

**Attributes:**
- `stage: PipelineStage | None`: Failed stage
- `cause: Exception | None`: Underlying exception

### Other Exceptions

```python
from resume_generator.extraction.profile import ExtractionError
from resume_generator.optimization.optimizer import OptimizationError
from resume_generator.optimization.tailoring import TailoringError
```

All inherit from `PipelineError`.

## Advanced Usage

### Custom Progress UI

```python
from resume_generator import ResumePipeline
from resume_generator.ui.progress import PipelineUI

ui = PipelineUI(verbose=True)
pipeline = ResumePipeline(ui=ui)

result = pipeline.run(sources=["resume.pdf"])
```

### Disable PDF Compilation

```python
from resume_generator.config import get_settings

settings = get_settings()
settings.compile_pdf = False

pipeline = ResumePipeline(settings=settings)
result = pipeline.run(sources=["resume.pdf"])

print(f"LaTeX file: {result.tex_path}")
```

### Custom Template Configuration

```python
from resume_generator import ResumePipeline
from resume_generator.config import ResumeTemplate, get_settings

settings = get_settings()
settings.default_template = ResumeTemplate.ATS
settings.primary_color = "#1E3A8A"
settings.font_body_size = 11

pipeline = ResumePipeline(settings=settings)
result = pipeline.run(sources=["resume.pdf"])
```

### Batch Processing

```python
from pathlib import Path
from resume_generator import ResumePipeline

pipeline = ResumePipeline()
resume_files = Path("resumes/").glob("*.pdf")

for resume_file in resume_files:
    try:
        result = pipeline.run(
            sources=[resume_file],
            output_path=Path(f"output/{resume_file.stem}_generated.pdf")
        )
        print(f"✓ {resume_file.name} → {result.output_path}")
    except Exception as e:
        print(f"✗ {resume_file.name}: {e}")
```

### Job Tailoring from URL

```python
from resume_generator import ResumePipeline
from resume_generator.models.job import JobDescription
import requests

job_url = "https://example.com/job/senior-python-dev"
response = requests.get(job_url)

job = JobDescription(
    title="Senior Python Developer",
    url=job_url,
    raw_text=response.text
)

pipeline = ResumePipeline()
result = pipeline.run(
    sources=["resume.pdf"],
    job=job
)
```

### Extract Profile Only

```python
from resume_generator.extraction.profile import ProfileExtractor
from resume_generator.ingestion.loader import DataLoader
from resume_generator.config import get_settings

settings = get_settings()
loader = DataLoader()
extractor = ProfileExtractor(settings)

load_result = loader.load(["resume.pdf"])
profile = extractor.extract(load_result.unified_text)

print(f"Name: {profile.name}")
print(f"Experiences: {len(profile.experiences)}")
print(f"Skills: {', '.join(profile.skills)}")
```

## Type Safety

All public APIs include comprehensive type hints. Use mypy or pyright for static type checking:

```bash
mypy your_script.py
pyright your_script.py
```

Example with full type annotations:

```python
from pathlib import Path
from resume_generator import ResumePipeline, PipelineResult
from resume_generator.config import Settings, get_settings, ResumeTemplate

def generate_resume(source_file: Path, output_file: Path) -> PipelineResult:
    settings: Settings = get_settings()
    settings.default_template = ResumeTemplate.MODERN

    pipeline: ResumePipeline = ResumePipeline(settings=settings)

    result: PipelineResult = pipeline.run(
        sources=[source_file],
        output_path=output_file
    )

    return result
```

## Testing

### Mocking the Pipeline

```python
from unittest.mock import Mock, patch
from resume_generator import ResumePipeline, PipelineResult

def test_resume_generation():
    mock_result = PipelineResult(
        success=True,
        pdf_path=Path("output/resume.pdf"),
        optimization_score=0.85
    )

    with patch.object(ResumePipeline, 'run', return_value=mock_result):
        pipeline = ResumePipeline()
        result = pipeline.run(sources=["resume.pdf"])

        assert result.success
        assert result.optimization_score == 0.85
```

## Best Practices

1. **Always use context managers or try/except for error handling**
2. **Set API key via environment variables, not hardcoded**
3. **Use type hints for better IDE support**
4. **Enable verbose mode during development**
5. **Cache results when processing multiple times**
6. **Use async pipeline for concurrent operations**
7. **Validate input files before processing**
8. **Monitor optimization and keyword match scores**

## Migration Guide

### From v0.0.x to v0.1.0

- `ResumePipeline.generate()` → `ResumePipeline.run()`
- Settings now use Pydantic v2
- All methods now have type hints
- Async support added with `run_async()`

## Support

For API questions and issues:
- GitHub Issues: https://github.com/sebastian/resume-generator/issues
- Documentation: https://github.com/sebastian/resume-generator/docs

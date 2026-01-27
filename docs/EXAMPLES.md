# Examples

Comprehensive examples for using Resume Generator in various scenarios.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Job Tailoring](#job-tailoring)
- [API Usage](#api-usage)
- [Advanced Scenarios](#advanced-scenarios)
- [Template Customization](#template-customization)
- [Integration Examples](#integration-examples)

## Basic Examples

### Example 1: Generate from Single PDF

**Input:**
```bash
resume-gen generate resume.pdf
```

**Output:**
```
[LOADING] Reading resume.pdf...
[EXTRACTING] Analyzing with Claude AI...
[OPTIMIZING] Applying X-Y-Z formula...
[GENERATING] Building LaTeX...
[COMPILING] Running pdflatex...

✓ Resume generated: output/john_doe_resume.pdf
  Optimization score: 0.85
  Total time: 24.3s
```

### Example 2: Multiple Input Sources

**Scenario:** Combine information from multiple files

**Input:**
```bash
resume-gen generate \
  old_resume.pdf \
  linkedin_export.txt \
  projects.md \
  certifications.txt
```

**Result:** Unified resume incorporating all sources

### Example 3: Generate LaTeX Only

**Input:**
```bash
resume-gen generate resume.pdf --no-compile -o resume.tex
```

**Use Case:** Manual LaTeX editing before PDF generation

**Follow-up:**
```bash
# Edit resume.tex manually
vim resume.tex

# Compile when ready
pdflatex resume.tex
```

## Job Tailoring

### Example 4: Inline Job Description

**Input:**
```bash
resume-gen generate resume.pdf \
  --job "Senior Python Developer with 5+ years experience.
  Required: Python, Django, PostgreSQL, Docker, AWS.
  Preferred: Redis, Celery, REST APIs."
```

**Result:** Resume optimized for Python/Django position with 72% keyword match

### Example 5: Job Description from File

**job_posting.txt:**
```
Senior Full Stack Engineer
Tech Startup Inc. | San Francisco, CA

We're seeking an experienced Full Stack Engineer to join our team.

Requirements:
- 5+ years software development experience
- Expert in React, Node.js, TypeScript
- Experience with PostgreSQL, Redis
- AWS cloud infrastructure knowledge
- Docker and Kubernetes
- REST API design
- Agile development practices

Preferred:
- GraphQL experience
- CI/CD pipeline setup
- Microservices architecture
- Open source contributions
```

**Input:**
```bash
resume-gen generate resume.pdf --job-file job_posting.txt
```

**Result:** Tailored resume highlighting relevant skills and experiences

### Example 6: Fetch Job from URL

**Input:**
```bash
resume-gen generate resume.pdf \
  --job-url https://example.com/careers/senior-python-dev \
  -t ats \
  -o tailored_resume.pdf
```

**Result:** ATS-optimized resume for online application

## API Usage

### Example 7: Basic Python API

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

if result.success:
    print(f"✓ Generated: {result.output_path}")
    print(f"  Score: {result.optimization_score:.2f}")
else:
    print(f"✗ Failed: {result.errors}")
```

### Example 8: Async Pipeline

```python
import asyncio
from pathlib import Path
from resume_generator import ResumePipeline

async def generate_resume():
    pipeline = ResumePipeline()

    result = await pipeline.run_async(
        sources=[Path("resume.pdf")],
        output_path=Path("output/resume.pdf")
    )

    return result

result = asyncio.run(generate_resume())
print(f"Generated in {result.total_duration_seconds:.1f}s")
```

### Example 9: With Job Tailoring

```python
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.models.job import JobDescription

job = JobDescription(
    title="Senior Python Developer",
    company="Tech Corp",
    raw_text="""
    Senior Python Developer position requiring 5+ years experience
    with Django, PostgreSQL, AWS, and Docker.
    """
)

pipeline = ResumePipeline()
result = pipeline.run(
    sources=[Path("resume.pdf")],
    job=job,
    output_path=Path("output/tailored_resume.pdf")
)

print(f"Keyword match: {result.keyword_match_rate:.0%}")
```

### Example 10: Custom Callbacks

```python
from resume_generator import ResumePipeline
from resume_generator.ui.progress import PipelineStage

def on_stage_start(stage: PipelineStage):
    print(f"Starting {stage.value}...")

def on_stage_complete(stage: PipelineStage, result):
    print(f"✓ {stage.value} done in {result.duration_seconds:.1f}s")

def on_error(stage: PipelineStage, error: Exception):
    print(f"✗ {stage.value} failed: {error}")

pipeline = ResumePipeline()
result = pipeline.run_with_callbacks(
    sources=["resume.pdf"],
    on_stage_start=on_stage_start,
    on_stage_complete=on_stage_complete,
    on_error=on_error
)
```

## Advanced Scenarios

### Example 11: Batch Processing

**Scenario:** Generate resumes for multiple people

**Script: `batch_generate.py`**
```python
from pathlib import Path
from resume_generator import ResumePipeline

def process_batch(input_dir: Path, output_dir: Path):
    pipeline = ResumePipeline()
    output_dir.mkdir(exist_ok=True)

    for pdf_file in input_dir.glob("*.pdf"):
        try:
            output_file = output_dir / f"{pdf_file.stem}_generated.pdf"

            result = pipeline.run(
                sources=[pdf_file],
                output_path=output_file
            )

            if result.success:
                print(f"✓ {pdf_file.name} → {output_file.name}")
            else:
                print(f"✗ {pdf_file.name}: {result.errors[0]}")

        except Exception as e:
            print(f"✗ {pdf_file.name}: {e}")

process_batch(Path("resumes/"), Path("output/"))
```

**Run:**
```bash
python batch_generate.py
```

### Example 12: Custom Template Colors

```python
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.config import get_settings, ResumeTemplate

settings = get_settings()
settings.default_template = ResumeTemplate.MODERN
settings.primary_color = "#1E3A8A"      # Deep blue
settings.secondary_color = "#3B82F6"     # Bright blue
settings.font_name_size = 22
settings.margin_inches = 0.65

pipeline = ResumePipeline(settings=settings)
result = pipeline.run(
    sources=[Path("resume.pdf")],
    output_path=Path("output/custom_style_resume.pdf")
)
```

### Example 13: Extract Profile Only (No Generation)

```python
from pathlib import Path
from resume_generator.config import get_settings
from resume_generator.ingestion.loader import DataLoader
from resume_generator.extraction.profile import ProfileExtractor

settings = get_settings()
loader = DataLoader()
extractor = ProfileExtractor(settings)

load_result = loader.load([Path("resume.pdf")])
profile = extractor.extract(load_result.unified_text)

print(f"Name: {profile.name}")
print(f"Email: {profile.email}")
print(f"Experiences: {len(profile.experiences)}")

for exp in profile.experiences:
    print(f"\n{exp.role} at {exp.company}")
    print(f"  {exp.start_date} - {exp.end_date}")
    for bullet in exp.bullets:
        print(f"  • {bullet}")

print(f"\nSkills: {', '.join(profile.skills)}")
```

### Example 14: Resume Comparison

```python
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.models.job import JobDescription

def compare_tailoring(resume_path: Path, jobs: list[JobDescription]):
    """Compare resume optimization for different jobs."""
    pipeline = ResumePipeline()
    results = []

    for job in jobs:
        result = pipeline.run(
            sources=[resume_path],
            job=job,
            output_path=Path(f"output/{job.title.replace(' ', '_')}.pdf")
        )

        results.append({
            'job': job.title,
            'keyword_match': result.keyword_match_rate,
            'optimization_score': result.optimization_score,
            'output': result.output_path
        })

    return results

jobs = [
    JobDescription(title="Senior Python Developer", raw_text="..."),
    JobDescription(title="Full Stack Engineer", raw_text="..."),
    JobDescription(title="DevOps Engineer", raw_text="..."),
]

results = compare_tailoring(Path("resume.pdf"), jobs)

for r in sorted(results, key=lambda x: x['keyword_match'], reverse=True):
    print(f"{r['job']}: {r['keyword_match']:.0%} match")
```

## Template Customization

### Example 15: Professional Academic Resume

```python
from resume_generator import ResumePipeline
from resume_generator.config import get_settings

settings = get_settings()
settings.default_template = ResumeTemplate.ATS  # Clean, simple
settings.primary_color = "#1a1a1a"  # Black
settings.font_body_size = 11
settings.margin_inches = 1.0  # Generous margins
settings.max_bullets_per_job = 4  # Concise

pipeline = ResumePipeline(settings=settings)
result = pipeline.run(sources=["cv.pdf"])
```

### Example 16: Creative Industry Resume

```python
from resume_generator import ResumePipeline
from resume_generator.config import get_settings

settings = get_settings()
settings.default_template = ResumeTemplate.MODERN
settings.primary_color = "#7C3AED"  # Purple
settings.secondary_color = "#EC4899"  # Pink
settings.font_name_size = 24  # Bold name
settings.margin_inches = 0.6  # Minimal margins

pipeline = ResumePipeline(settings=settings)
result = pipeline.run(sources=["portfolio.pdf"])
```

## Integration Examples

### Example 17: GitHub Actions CI/CD

**.github/workflows/generate-resume.yml:**
```yaml
name: Generate Resume

on:
  push:
    paths:
      - 'resume/**'

jobs:
  generate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install LaTeX
        run: |
          sudo apt-get update
          sudo apt-get install -y texlive-latex-base texlive-fonts-recommended

      - name: Install Claude CLI
        run: |
          # Follow https://github.com/anthropics/claude-code for installation

      - name: Install Resume Generator
        run: pip install resume-generator

      - name: Generate Resume
        env:
          RESUME_GEN_CLAUDE_MODEL: sonnet
        run: |
          resume-gen generate resume/source.pdf -o dist/resume.pdf

      - name: Upload Artifact
        uses: actions/upload-artifact@v3
        with:
          name: resume
          path: dist/resume.pdf
```

### Example 18: Pre-commit Hook

**.git/hooks/pre-commit:**
```bash
#!/bin/bash

if [ -f "resume_data/resume.pdf" ]; then
  echo "Generating updated resume..."
  resume-gen generate resume_data/resume.pdf -o dist/resume.pdf

  if [ $? -eq 0 ]; then
    echo "✓ Resume generated successfully"
    git add dist/resume.pdf
  else
    echo "✗ Resume generation failed"
    exit 1
  fi
fi
```

### Example 19: Flask Web Service

```python
from flask import Flask, request, send_file
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.models.job import JobDescription

app = Flask(__name__)
pipeline = ResumePipeline()

@app.route('/generate', methods=['POST'])
def generate_resume():
    file = request.files['resume']
    job_text = request.form.get('job_description')

    input_path = Path(f"/tmp/{file.filename}")
    output_path = Path(f"/tmp/output_{file.filename}")

    file.save(input_path)

    job = JobDescription(
        title="Custom",
        raw_text=job_text
    ) if job_text else None

    result = pipeline.run(
        sources=[input_path],
        job=job,
        output_path=output_path
    )

    if result.success:
        return send_file(result.output_path, as_attachment=True)
    else:
        return {'error': result.errors}, 500

if __name__ == '__main__':
    app.run(port=5000)
```

### Example 20: Django Management Command

**resumes/management/commands/generate_resume.py:**
```python
from django.core.management.base import BaseCommand
from pathlib import Path
from resume_generator import ResumePipeline

class Command(BaseCommand):
    help = 'Generate optimized resume from source files'

    def add_arguments(self, parser):
        parser.add_argument('source', type=str)
        parser.add_argument('--output', type=str, default='output.pdf')
        parser.add_argument('--job', type=str, required=False)

    def handle(self, *args, **options):
        pipeline = ResumePipeline()

        result = pipeline.run(
            sources=[Path(options['source'])],
            output_path=Path(options['output']),
        )

        if result.success:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Generated: {result.output_path}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed: {result.errors}")
            )
```

**Usage:**
```bash
python manage.py generate_resume resume.pdf --output media/resume.pdf
```

## Common Patterns

### Pattern 1: Error Handling

```python
from resume_generator import ResumePipeline, PipelineError

try:
    pipeline = ResumePipeline()
    result = pipeline.run(sources=["resume.pdf"])

    if not result.success:
        print(f"Generation failed: {result.errors}")
except PipelineError as e:
    print(f"Pipeline error at {e.stage}: {e}")
    if e.cause:
        print(f"Caused by: {e.cause}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Pattern 2: Configuration Management

```python
from resume_generator.config import Settings, get_settings

def get_production_settings() -> Settings:
    settings = get_settings()
    settings.verbose = False
    settings.compile_pdf = True
    settings.api_timeout = 120.0
    return settings

def get_development_settings() -> Settings:
    settings = get_settings()
    settings.verbose = True
    settings.compile_pdf = False
    settings.keep_latex_source = True
    return settings
```

### Pattern 3: Progress Monitoring

```python
from resume_generator import ResumePipeline
from resume_generator.ui.progress import PipelineUI

ui = PipelineUI(verbose=True)
pipeline = ResumePipeline(ui=ui)

result = pipeline.run(sources=["resume.pdf"])

print(f"\nStatistics:")
print(f"  Files loaded: {ui.stats.files_loaded}")
print(f"  Experiences: {ui.stats.experiences_extracted}")
print(f"  Skills: {ui.stats.skills_extracted}")
print(f"  Bullets optimized: {ui.stats.bullets_optimized}")
print(f"  Optimization score: {ui.stats.optimization_score:.2f}")
print(f"  Keyword match: {ui.stats.keyword_match_rate:.0%}")
```

## Next Steps

- Review [API_REFERENCE.md](./API_REFERENCE.md) for complete API documentation
- Check [CLI_GUIDE.md](./CLI_GUIDE.md) for command-line usage
- See [CONFIGURATION.md](./CONFIGURATION.md) for all settings options
- Read [CONTRIBUTING.md](./CONTRIBUTING.md) to contribute examples

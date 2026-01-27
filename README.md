# Resume Generator

**S+ tier resume generator powered by Claude AI**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Generate professional, ATS-optimized resumes from raw data using Claude AI. Transform PDFs, markdown files, or raw text into beautifully formatted LaTeX/PDF resumes tailored to specific job positions.

## Features

- **Multi-format Input**: Process PDF, TXT, MD files or directories
- **AI-Powered Extraction**: Claude AI extracts and structures your professional profile
- **X-Y-Z Formula Optimization**: Automatically reformats bullets using proven impact formulas
- **Job Tailoring**: Optimize resume for specific job descriptions (from text, file, or URL)
- **Research-Backed Templates**: Modern and ATS-friendly LaTeX templates
- **Colorful Progress UI**: Beautiful terminal interface with real-time progress tracking
- **PDF Compilation**: Automatic LaTeX-to-PDF compilation
- **Type-Safe**: Full type hints with mypy/pyright validation
- **Async Support**: Asynchronous pipeline execution for better performance

## Quick Start

### Prerequisites

- Python 3.11 or higher
- `pdflatex` (for PDF compilation)
- Anthropic API key

**Install LaTeX on Ubuntu/Debian:**
```bash
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**Install LaTeX on macOS:**
```bash
brew install --cask mactex
```

### Installation

```bash
# Clone the repository
git clone https://github.com/sebastian/resume-generator.git
cd resume-generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

Set your Anthropic API key:

```bash
export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."
```

Or create a `.env` file:

```bash
RESUME_GEN_ANTHROPIC_API_KEY=sk-ant-...
RESUME_GEN_CLAUDE_MODEL=claude-sonnet-4-20250514
```

## Usage

### Basic Examples

**Generate from a single PDF:**
```bash
resume-gen generate ./my_resume.pdf
```

**Generate from multiple files:**
```bash
resume-gen generate ./resume.pdf ./experience.md ./skills.txt
```

**Generate from a directory:**
```bash
resume-gen generate ./resume_data/
```

### Job Tailoring

**Tailor for a job (from text):**
```bash
resume-gen generate ./data/ --job "Senior Python Developer with 5+ years experience..."
```

**Tailor using a job description file:**
```bash
resume-gen generate ./data/ --job-file job_posting.txt
```

**Fetch job description from URL:**
```bash
resume-gen generate ./data/ --job-url https://example.com/careers/senior-python-dev
```

### Output Options

**Specify output path:**
```bash
resume-gen generate ./data/ -o ./output/my_resume.pdf
```

**Choose template:**
```bash
resume-gen generate ./data/ -t ats  # ATS-friendly template
resume-gen generate ./data/ -t modern  # Modern design template
```

**LaTeX only (skip PDF compilation):**
```bash
resume-gen generate ./data/ --no-compile
```

**Verbose output for debugging:**
```bash
resume-gen generate ./data/ -V
```

### Complete Example

```bash
resume-gen generate \
  ./resume_data/ \
  --job-url https://example.com/job/senior-python-dev \
  --template modern \
  --output ./output/tailored_resume.pdf \
  --verbose
```

## Python API

### Synchronous Pipeline

```python
from pathlib import Path
from resume_generator import ResumePipeline
from resume_generator.config import ResumeTemplate, get_settings
from resume_generator.models.job import JobDescription

# Initialize pipeline
settings = get_settings()
pipeline = ResumePipeline(settings=settings)

# Run pipeline
result = pipeline.run(
    sources=[Path("./resume.pdf"), Path("./experience.md")],
    output_path=Path("./output/resume.pdf"),
    job=JobDescription(
        title="Senior Python Developer",
        raw_text="Looking for a Python expert with...",
    ),
    template=ResumeTemplate.MODERN,
)

if result.success:
    print(f"Resume generated: {result.output_path}")
    print(f"Optimization score: {result.optimization_score:.2f}")
    print(f"Keyword match rate: {result.keyword_match_rate:.0%}")
```

### Asynchronous Pipeline

```python
import asyncio
from pathlib import Path
from resume_generator import ResumePipeline

async def generate_resume():
    pipeline = ResumePipeline()
    result = await pipeline.run_async(
        sources=["./data/resume.pdf"],
        output_path=Path("./output/resume.pdf"),
    )
    return result

result = asyncio.run(generate_resume())
```

### With Custom Progress Tracking

```python
from resume_generator.ui.progress import PipelineUI, PipelineStage

def on_stage_complete(stage: PipelineStage, result):
    print(f"✓ {stage.value} completed in {result.duration_seconds:.2f}s")

ui = PipelineUI(verbose=True)
pipeline = ResumePipeline(ui=ui)

result = pipeline.run_with_callbacks(
    sources=["./data/"],
    on_stage_complete=on_stage_complete,
)
```

## Project Structure

```
resume-generator/
├── src/resume_generator/
│   ├── ingestion/           # Input file loading (PDF, TXT, MD)
│   │   ├── base.py         # Base extractor interface
│   │   ├── pdf.py          # PDF extraction
│   │   ├── text.py         # Text file extraction
│   │   └── loader.py       # Multi-source data loader
│   ├── extraction/          # AI-powered profile extraction
│   │   ├── profile.py      # Profile extractor using Claude
│   │   └── prompts.py      # Extraction prompts
│   ├── optimization/        # Resume optimization
│   │   ├── optimizer.py    # X-Y-Z formula optimization
│   │   ├── tailoring.py    # Job-specific tailoring
│   │   └── prompts.py      # Optimization prompts
│   ├── generation/          # LaTeX/PDF generation
│   │   ├── generator.py    # LaTeX template engine
│   │   ├── compiler.py     # PDF compilation
│   │   └── templates/      # LaTeX templates
│   ├── models/              # Data models
│   │   ├── profile.py      # Person profile model
│   │   ├── resume.py       # Resume document model
│   │   └── job.py          # Job description model
│   ├── ui/                  # User interface
│   │   └── progress.py     # Terminal progress UI
│   ├── config.py            # Configuration and settings
│   ├── pipeline.py          # Main pipeline orchestration
│   └── main.py              # CLI entry point
├── tests/                   # Comprehensive test suite
├── pyproject.toml           # Project configuration
└── README.md
```

## Configuration

All settings can be configured via environment variables or `.env` file with the `RESUME_GEN_` prefix.

### API Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *required* | Anthropic API key for Claude |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `MAX_TOKENS` | `4096` | Maximum tokens for Claude responses |
| `API_TIMEOUT` | `120.0` | API request timeout (seconds) |
| `API_MAX_RETRIES` | `3` | Maximum retry attempts |

### Path Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `./output` | Output directory for resumes |
| `CACHE_DIR` | `./.resume_cache` | Cache directory |

### Template & Design Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_TEMPLATE` | `modern` | Default template (`modern`, `ats`) |
| `PRIMARY_COLOR` | `#2C3E50` | Primary color (hex) |
| `SECONDARY_COLOR` | `#3498DB` | Secondary color (hex) |
| `FONT_NAME_SIZE` | `20` | Name font size (18-24) |
| `FONT_HEADER_SIZE` | `14` | Header font size (12-16) |
| `FONT_BODY_SIZE` | `11` | Body font size (10-12) |
| `MARGIN_INCHES` | `0.75` | Page margins (0.5-1.0) |

### Content Optimization

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BULLETS_PER_JOB` | `3` | Minimum bullets per job (2-5) |
| `MAX_BULLETS_PER_JOB` | `5` | Maximum bullets per job (3-7) |
| `SUMMARY_MIN_WORDS` | `50` | Minimum summary words (30-80) |
| `SUMMARY_MAX_WORDS` | `100` | Maximum summary words (80-150) |
| `TARGET_KEYWORD_MATCH_RATE` | `0.70` | Target keyword match (0.5-0.9) |
| `TAILORING_CUSTOMIZATION_RATE` | `0.50` | Customization level (0.3-0.7) |

### Pipeline Options

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_JOB_TAILORING` | `true` | Enable job-specific optimization |
| `COMPILE_PDF` | `true` | Compile LaTeX to PDF |
| `KEEP_LATEX_SOURCE` | `true` | Keep generated LaTeX file |
| `VERBOSE` | `false` | Enable verbose output |

### Example `.env` File

```bash
RESUME_GEN_ANTHROPIC_API_KEY=sk-ant-...
RESUME_GEN_CLAUDE_MODEL=claude-sonnet-4-20250514
RESUME_GEN_DEFAULT_TEMPLATE=modern
RESUME_GEN_PRIMARY_COLOR=#1E3A8A
RESUME_GEN_COMPILE_PDF=true
RESUME_GEN_VERBOSE=false
```

## Pipeline Stages

The resume generation pipeline consists of the following stages:

1. **Loading**: Read and extract text from input sources
2. **Extracting**: Use Claude AI to extract structured profile data
3. **Optimizing**: Apply X-Y-Z formula to optimize bullet points
4. **Tailoring** *(optional)*: Customize resume for specific job
5. **Generating**: Build LaTeX document from optimized data
6. **Compiling** *(optional)*: Compile LaTeX to PDF

Each stage is tracked with a beautiful progress UI showing:
- Stage status and progress
- Files loaded
- Experiences/skills extracted
- Bullets optimized
- Keyword match rate
- Optimization score

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=resume_generator --cov-report=html

# Type checking
mypy src/
pyright src/

# Linting
ruff check src/ tests/
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_ingestion.py

# With verbose output
pytest -v

# With coverage
pytest --cov=resume_generator --cov-report=term-missing
```

### Code Quality

The project maintains high code quality standards:
- **Type Safety**: Full type hints, checked with mypy (strict mode) and pyright
- **Linting**: Ruff for fast linting and formatting
- **Testing**: Comprehensive test suite with pytest
- **Coverage**: High test coverage across all modules

## Templates

### Modern Template

Professional, visually appealing design with:
- Two-column layout
- Color accents for section headers
- Clean typography
- Optimal white space

### ATS Template

ATS-friendly design optimized for:
- Single-column layout
- Simple formatting
- Machine-readable structure
- No complex graphics

## Troubleshooting

### LaTeX Compilation Fails

**Problem**: `pdflatex` command not found

**Solution**: Install LaTeX distribution (see Prerequisites section)

### API Key Errors

**Problem**: `anthropic_api_key is required`

**Solution**: Set `RESUME_GEN_ANTHROPIC_API_KEY` environment variable or create `.env` file

### PDF Extraction Issues

**Problem**: Unable to extract text from PDF

**Solution**: Ensure PDF contains selectable text (not scanned images). For scanned PDFs, use OCR preprocessing.

### Out of Memory

**Problem**: Large files cause memory issues

**Solution**: Process files individually or increase system memory. Consider splitting large PDFs.

## Research Foundations

This project is built on extensive research into resume best practices:

- **X-Y-Z Formula**: "Accomplished [X] as measured by [Y], by doing [Z]"
- **ATS Optimization**: Keyword matching, simple formatting, machine readability
- **Visual Hierarchy**: Strategic use of whitespace, typography, and color
- **Content Optimization**: Impact-focused bullet points, quantified achievements
- **Tailoring Strategies**: 65-80% keyword match rate, balanced customization

Research documentation is available in the `research-results/` directory.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass and type checking succeeds
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details

## Acknowledgments

- Powered by [Anthropic Claude](https://www.anthropic.com/claude)
- LaTeX templates inspired by resume research and best practices
- Built with Python 3.11+, Pydantic, Rich, and modern async patterns

## Support

For issues, questions, or contributions:
- GitHub Issues: [https://github.com/sebastian/resume-generator/issues](https://github.com/sebastian/resume-generator/issues)
- Documentation: This README and inline code documentation
- Examples: See `tests/` directory for comprehensive usage examples

---

**Made with ❤️ using Claude AI**

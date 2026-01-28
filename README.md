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
- Claude CLI (for AI-powered features)

**Install Claude CLI:**

```bash
# macOS/Linux (via Homebrew)
brew install anthropic-cli

# Or download from https://github.com/anthropics/claude-code
# Follow the official installation instructions
```

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

**Option 1: YAML Configuration File (Recommended)**

```bash
# Create a config file
resume-gen init

# Edit the generated resume-gen.yaml
```

Example `resume-gen.yaml`:
```yaml
max_pages: 1
max_bullet_words: 25
color_palette: burgundy
claude_model: sonnet
output_language: en
```

**Option 2: Environment Variables**

```bash
export RESUME_GEN_CLAUDE_MODEL=sonnet
```

Or create a `.env` file:

```bash
RESUME_GEN_CLAUDE_MODEL=sonnet
RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600
```

See [Configuration Documentation](docs/CONFIGURATION.md) for all options.

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

**Specify Claude model:**
```bash
resume-gen generate ./data/ --claude-model opus
```

**Use a color palette:**
```bash
resume-gen generate ./data/ --colors burgundy
```

Available palettes: `classic`, `burgundy`, `navy`, `forest`, `slate`, `charcoal`

**Limit pages and bullet length:**
```bash
resume-gen generate ./data/ --max-pages 1 --max-bullet-words 20
```

**Use a custom config file:**
```bash
resume-gen generate ./data/ --config my-config.yaml
```

### Complete Example

```bash
resume-gen generate \
  ./resume_data/ \
  --job-url https://example.com/job/senior-python-dev \
  --template modern \
  --output ./output/tailored_resume.pdf \
  --claude-model sonnet \
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
│   │   ├── profile.py      # Profile extractor using Claude CLI
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
│   ├── utils/               # Utility modules
│   │   ├── json_parser.py  # JSON parsing utilities
│   │   └── cli.py          # CLI utilities
│   ├── claude_client.py     # Claude CLI subprocess client
│   ├── config.py            # Configuration and settings
│   ├── pipeline.py          # Main pipeline orchestration
│   └── main.py              # CLI entry point
├── tests/                   # Comprehensive test suite
├── pyproject.toml           # Project configuration
└── README.md
```

## Configuration

Configuration can be set via YAML file, environment variables, or CLI options (in order of precedence: CLI > YAML > ENV > defaults).

### YAML Configuration File

Create a `resume-gen.yaml` file in your project directory:

```bash
resume-gen init  # Creates a template config file
```

Example configuration:
```yaml
# Output constraints
max_pages: 1              # Maximum pages (1-3)
max_bullet_words: 25      # Max words per bullet (10-50)

# Design
color_palette: classic    # classic, burgundy, navy, forest, slate, charcoal

# AI
claude_model: sonnet      # sonnet, opus, haiku

# Content
min_bullets_per_job: 3
max_bullets_per_job: 5
output_language: en
```

### Color Palettes

| Palette | Primary | Secondary | Best For |
|---------|---------|-----------|----------|
| `classic` | Dark blue | Bright blue | Traditional corporate |
| `burgundy` | Burgundy | Gray | Elegant/executive |
| `navy` | Navy | Slate blue | Finance/legal |
| `forest` | Forest green | Olive | Environmental/creative |
| `slate` | Slate gray | Gray | Modern minimalist |
| `charcoal` | Charcoal | Slate | Tech/startup |

### Environment Variables

All settings can also be configured via environment variables with the `RESUME_GEN_` prefix:

```bash
export RESUME_GEN_CLAUDE_MODEL=sonnet
export RESUME_GEN_MAX_PAGES=1
export RESUME_GEN_COLOR_PALETTE=burgundy
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for complete reference.

## Pipeline Stages

The resume generation pipeline consists of the following stages:

1. **Loading**: Read and extract text from input sources
2. **Extracting**: Use Claude CLI to extract structured profile data
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

### Claude CLI Not Found

**Problem**: `Claude CLI not available. Please install Claude CLI.`

**Solution**: Install the Claude CLI following the prerequisites section. Ensure the `claude` binary is in your PATH.

```bash
# Verify installation
claude --version
```

### LaTeX Compilation Fails

**Problem**: `pdflatex` command not found

**Solution**: Install LaTeX distribution (see Prerequisites section)

### PDF Extraction Issues

**Problem**: Unable to extract text from PDF

**Solution**: Ensure PDF contains selectable text (not scanned images). For scanned PDFs, use OCR preprocessing.

### Out of Memory

**Problem**: Large files cause memory issues

**Solution**: Process files individually or increase system memory. Consider splitting large PDFs.

### Claude CLI Timeout

**Problem**: AI operations taking too long

**Solution**: Increase the timeout value:

```bash
export RESUME_GEN_CLAUDE_CLI_TIMEOUT=7200  # 2 hours
```

Or specify in `.env`:

```bash
RESUME_GEN_CLAUDE_CLI_TIMEOUT=7200
```

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

- Powered by [Claude CLI](https://github.com/anthropics/claude-code) from Anthropic
- LaTeX templates inspired by resume research and best practices
- Built with Python 3.11+, Pydantic, Rich, and modern async patterns

## Support

For issues, questions, or contributions:
- GitHub Issues: [https://github.com/sebastian/resume-generator/issues](https://github.com/sebastian/resume-generator/issues)
- Documentation: This README and inline code documentation
- Examples: See `tests/` directory for comprehensive usage examples

---

**Made with ❤️ using Claude AI**

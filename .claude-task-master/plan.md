## Task List

Now I have a comprehensive understanding of the project. Let me create the master plan.

---

# S+ Tier Resume Generator - Master Implementation Plan

## Project Overview

This project creates a professional Python-based resume generation pipeline that:
1. **Ingests raw data** (PDFs, text, markdown) about a job applicant
2. **Processes with Claude AI** to extract, structure, and optimize content
3. **Generates S+ tier resumes** in LaTeX/PDF using research-backed principles
4. **Optionally optimizes for specific job positions**
5. **Displays colorful progress tracking** in terminal using Rich

## Architecture Overview

```
resume_generator/
├── src/
│   └── resume_generator/
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── config.py            # Configuration and settings
│       ├── pipeline.py          # Main orchestration
│       ├── ingestion/           # Data input handling
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract base extractor
│       │   ├── pdf.py           # PDF text extraction
│       │   ├── text.py          # Plain text/markdown
│       │   └── loader.py        # Unified loader
│       ├── extraction/          # Claude-powered data extraction
│       │   ├── __init__.py
│       │   ├── profile.py       # Extract structured profile
│       │   └── prompts.py       # Extraction prompts
│       ├── optimization/        # Content optimization
│       │   ├── __init__.py
│       │   ├── optimizer.py     # Resume content optimizer
│       │   ├── tailoring.py     # Job-specific tailoring
│       │   └── prompts.py       # Optimization prompts
│       ├── generation/          # LaTeX generation
│       │   ├── __init__.py
│       │   ├── generator.py     # LaTeX document builder
│       │   ├── templates/       # LaTeX templates
│       │   │   ├── modern.tex   # Modern single-column
│       │   │   └── ats.tex      # ATS-optimized
│       │   └── compiler.py      # pdflatex compilation
│       ├── models/              # Pydantic data models
│       │   ├── __init__.py
│       │   ├── profile.py       # Person profile schema
│       │   ├── resume.py        # Resume structure schema
│       │   └── job.py           # Job description schema
│       └── ui/                  # Terminal UI
│           ├── __init__.py
│           └── progress.py      # Rich progress displays
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py
│   ├── test_extraction.py
│   ├── test_optimization.py
│   └── test_generation.py
├── pyproject.toml
└── README.md
```

## Research Integration Summary

From the research documents, key principles to implement:

**Design Guide:**
- 30:70 content-to-white-space ratio
- Font sizes: Name 18-24pt, headers 14-16pt, body 10-12pt
- Single-column layout for ATS compatibility
- Maximum 3 colors (primary, secondary, accent)
- Standard margins: 0.5-1 inch
- Standard section headers for ATS recognition

**Content Optimization Guide:**
- Google X-Y-Z formula for achievements
- Keywords: aim for 65-80% match rate
- Professional summary (50-100 words) instead of objective
- 3-5 bullet points per position with action verbs
- Quantified achievements (2.5x more interviews)
- Tailoring: 40-60% customization per application

---

### PR 1: Project Foundation & Data Models

- [x] `[quick]` Initialize git repository and create feature branch `feat/resume-generator-mvp`
- [x] `[coding]` Create `pyproject.toml` with dependencies: `anthropic>=0.40.0`, `pydantic>=2.0`, `rich>=13.0`, `pypdf>=4.0`, `aiofiles>=23.0`, `typer>=0.9.0`
- [x] `[coding]` Create `src/resume_generator/__init__.py` with version and package metadata
- [x] `[coding]` Create `src/resume_generator/config.py` with `Settings` Pydantic model for API keys, paths, and pipeline options
- [x] `[coding]` Create `src/resume_generator/models/profile.py` with Pydantic models: `ContactInfo`, `Experience`, `Education`, `Skill`, `Certification`, `PersonProfile`
- [x] `[coding]` Create `src/resume_generator/models/resume.py` with Pydantic models: `ResumeBullet`, `ResumeExperience`, `ResumeSection`, `ResumeDocument`
- [x] `[coding]` Create `src/resume_generator/models/job.py` with Pydantic models: `JobRequirement`, `JobDescription` for job position parsing

---

### PR 2: Data Ingestion Layer

- [x] `[coding]` Create `src/resume_generator/ingestion/base.py` with abstract `BaseExtractor` class defining `extract(path: Path) -> str` interface
- [ ] `[coding]` Create `src/resume_generator/ingestion/pdf.py` with `PDFExtractor` class using `pypdf` to extract text from PDF files
- [ ] `[coding]` Create `src/resume_generator/ingestion/text.py` with `TextExtractor` class handling `.txt`, `.md`, and raw text input
- [ ] `[coding]` Create `src/resume_generator/ingestion/loader.py` with `DataLoader` class that auto-detects file types, aggregates content from multiple sources, and returns unified text

---

### PR 3: Claude-Powered Extraction

- [ ] `[coding]` Create `src/resume_generator/extraction/prompts.py` with prompt templates for extracting structured profile data from raw text
- [ ] `[coding]` Create `src/resume_generator/extraction/profile.py` with `ProfileExtractor` class using Anthropic SDK to call Claude and parse response into `PersonProfile` model
- [ ] `[coding]` Implement `ProfileExtractor.extract()` method with structured output parsing via Claude's JSON mode
- [ ] `[quick]` Add retry logic with exponential backoff for API calls in `ProfileExtractor`

---

### PR 4: Content Optimization with Claude

- [ ] `[coding]` Create `src/resume_generator/optimization/prompts.py` with prompts implementing research principles: X-Y-Z formula, action verbs, quantified achievements
- [ ] `[coding]` Create `src/resume_generator/optimization/optimizer.py` with `ResumeOptimizer` class that transforms `PersonProfile` into `ResumeDocument` using Claude
- [ ] `[coding]` Create `src/resume_generator/optimization/tailoring.py` with `JobTailorer` class that optimizes resume content for specific job descriptions (keyword matching, bullet reordering, summary customization)
- [ ] `[coding]` Implement keyword extraction and matching score calculation in `tailoring.py`

---

### PR 5: LaTeX Generation & Compilation

- [ ] `[coding]` Create `src/resume_generator/generation/templates/modern.tex` - a modern, ATS-compatible single-column LaTeX template with configurable colors and styling following research guidelines
- [ ] `[coding]` Create `src/resume_generator/generation/templates/ats.tex` - a minimal ATS-optimized template (no graphics, single column, standard fonts)
- [ ] `[coding]` Create `src/resume_generator/generation/generator.py` with `LaTeXGenerator` class that converts `ResumeDocument` to LaTeX source using Jinja2 templating
- [ ] `[coding]` Create `src/resume_generator/generation/compiler.py` with `PDFCompiler` class that invokes `pdflatex` and handles compilation errors
- [ ] `[coding]` Implement proper LaTeX escaping for special characters in `generator.py`

---

### PR 6: Rich Terminal UI & Progress Tracking

- [ ] `[coding]` Create `src/resume_generator/ui/progress.py` with `PipelineUI` class using Rich library for colorful console output
- [ ] `[coding]` Implement `PipelineUI` methods: `start_pipeline()`, `update_stage()`, `show_progress()`, `show_success()`, `show_error()` with Rich panels, progress bars, and spinners
- [ ] `[coding]` Add stage-by-stage progress visualization with Rich Live display: "📄 Loading Data", "🔍 Extracting Profile", "✨ Optimizing Content", "📝 Generating LaTeX", "🖨️ Compiling PDF"
- [ ] `[coding]` Implement summary panel showing extraction stats, optimization score, and output path

---

### PR 7: Pipeline Orchestration & CLI

- [ ] `[coding]` Create `src/resume_generator/pipeline.py` with `ResumePipeline` class orchestrating: ingestion → extraction → optimization → generation → compilation
- [ ] `[coding]` Implement async pipeline execution with proper error handling and stage tracking
- [ ] `[coding]` Create `src/resume_generator/main.py` with Typer CLI: `generate` command accepting input paths, job description (optional), output path, and template selection
- [ ] `[coding]` Add CLI options: `--job-url` for job posting URL, `--template` for template selection, `--output` for output path, `--verbose` for debug output
- [ ] `[quick]` Add CLI entry point in `pyproject.toml` under `[project.scripts]`: `resume-gen = "resume_generator.main:app"`

---

### PR 8: Testing & Quality Assurance

- [ ] `[general]` Create `tests/conftest.py` with pytest fixtures for sample data, mock Claude responses, and temporary directories
- [ ] `[general]` Create `tests/test_ingestion.py` with unit tests for `PDFExtractor`, `TextExtractor`, and `DataLoader`
- [ ] `[general]` Create `tests/test_extraction.py` with tests for `ProfileExtractor` using mocked API responses
- [ ] `[general]` Create `tests/test_optimization.py` with tests for `ResumeOptimizer` and `JobTailorer`
- [ ] `[general]` Create `tests/test_generation.py` with tests for `LaTeXGenerator` and `PDFCompiler`
- [ ] `[coding]` Run full test suite and fix any failures: `pytest tests/ -v`
- [ ] `[quick]` Add type checking with `pyright` or `mypy` configuration in `pyproject.toml`

---

### PR 9: Documentation & Final Polish

- [ ] `[general]` Create comprehensive `README.md` with installation, usage examples, and configuration guide
- [ ] `[quick]` Add example input files in `examples/` directory
- [ ] `[general]` Run end-to-end test with real data from `resumes/` directory
- [ ] `[quick]` Final cleanup: remove unused imports, ensure consistent formatting with `ruff`

---

## Success Criteria

1. **Functional Pipeline**: Running `resume-gen generate ./input_data/ --output ./resume.pdf` produces a valid PDF resume
2. **Job Tailoring Works**: Adding `--job-url <url>` or `--job-description <text>` optimizes resume for that position
3. **Rich UI Displays**: Terminal shows colorful progress with stages, spinners, and completion summary
4. **Tests Pass**: `pytest tests/ -v` completes with 100% pass rate
5. **Type Checking Clean**: `pyright src/` or `mypy src/` reports no errors
6. **Research Principles Applied**: Generated resumes follow documented best practices (X-Y-Z formula, proper structure, ATS compatibility)
7. **PDF Compilation Succeeds**: `pdflatex` compiles without errors on generated LaTeX

---

PLANNING COMPLETE
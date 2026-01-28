# Resume Generator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Generate professional, ATS-optimized PDF resumes from your existing documents using Claude AI.

## Prerequisites

1. **Python 3.11+**

2. **Claude CLI** - [Install from GitHub](https://github.com/anthropics/claude-code)

3. **LaTeX** (for PDF generation)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra

   # macOS
   brew install --cask mactex
   ```

## Installation

```bash
git clone https://github.com/sebastian/resume-generator.git
cd resume-generator
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Setup

### 1. Create your config file

```bash
resume-gen init
```

This creates `resume-gen.yaml`. Edit it to set your preferences:

```yaml
# Where your resume source files live
input_dir: ./resume_data

# Where to save job descriptions you're applying to
target_job_dir: ./jobs

# Output settings
max_pages: 1
color_palette: burgundy      # classic, burgundy, navy, forest, slate, charcoal
claude_model: sonnet         # sonnet, opus, haiku
output_language: en
```

See `resume-gen.yaml.example` for all available options.

### 2. Organize your files

Put your resume source files (PDF, TXT, MD, DOCX) in your `input_dir`:

```
resume_data/
  resume.pdf
  linkedin_export.txt
  additional_experience.md
```

### 3. Add a job description (optional)

To tailor your resume, drop a job posting into your `target_job_dir`:

```
jobs/
  senior_python_dev.txt
```

The tool will automatically use the most recent file in this directory.

## Usage

Once configured, generating a resume is simple:

```bash
resume-gen generate
```

That's it. The tool reads your config, loads your source files, and outputs a tailored PDF.

### Overriding config for one-off runs

You can override any config setting via CLI:

```bash
resume-gen generate --colors navy --max-pages 2
resume-gen generate --job-url https://example.com/job-posting
resume-gen generate ./other_resume.pdf --output ./custom_output.pdf
```

## Troubleshooting

**Claude CLI not found**: Make sure `claude --version` works. If not, reinstall from the [Claude CLI repo](https://github.com/anthropics/claude-code).

**LaTeX compilation fails**: Install the LaTeX packages listed in Prerequisites.

**Timeout errors**: Increase timeout in config or env:
```bash
export RESUME_GEN_CLAUDE_CLI_TIMEOUT=7200
```

## License

MIT

# CLI Guide

## Overview

The `resume-gen` command-line tool provides a simple interface for generating professional resumes from various input sources. This guide covers all CLI commands, options, and usage patterns.

## Installation

```bash
pip install resume-generator
```

Verify installation:
```bash
resume-gen --version
```

## Prerequisites

### Required
- Python 3.11 or higher
- Anthropic API key

### Optional
- `pdflatex` for PDF compilation (install LaTeX)

### LaTeX Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**macOS:**
```bash
brew install --cask mactex
```

**Windows:**
Download and install [MiKTeX](https://miktex.org/download)

## Configuration

### API Key Setup

Set your Anthropic API key using one of these methods:

**1. Environment Variable:**
```bash
export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."
```

**2. .env File:**
```bash
echo 'RESUME_GEN_ANTHROPIC_API_KEY=sk-ant-...' > .env
```

**3. Shell Profile (.bashrc, .zshrc):**
```bash
echo 'export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc
```

## Basic Usage

### Generate Command

```bash
resume-gen generate [OPTIONS] SOURCES...
```

**SOURCES**: One or more input files, directories, or text

### Quick Examples

**Generate from a single PDF:**
```bash
resume-gen generate resume.pdf
```

**Generate from multiple files:**
```bash
resume-gen generate resume.pdf experience.md skills.txt
```

**Generate from a directory:**
```bash
resume-gen generate ./resume_data/
```

**Generate with custom output:**
```bash
resume-gen generate resume.pdf -o my_resume.pdf
```

## Command Options

### Input Options

#### `SOURCES` (required)
Input sources for resume generation.

**Types:**
- PDF files (`.pdf`)
- Text files (`.txt`)
- Markdown files (`.md`)
- Directories (processes all supported files)

**Examples:**
```bash
resume-gen generate resume.pdf
resume-gen generate resume.pdf experience.md
resume-gen generate ./data/
```

### Output Options

#### `-o, --output PATH`
Specify output file path.

**Default:** Auto-generated based on name and job title

**Examples:**
```bash
resume-gen generate resume.pdf -o john_doe_resume.pdf
resume-gen generate resume.pdf --output ./output/resume.pdf
```

#### `--no-compile`
Generate LaTeX only, skip PDF compilation.

**Use when:** You want to manually edit LaTeX before compilation

**Example:**
```bash
resume-gen generate resume.pdf --no-compile
```

### Job Tailoring Options

#### `--job TEXT`
Provide job description as inline text.

**Example:**
```bash
resume-gen generate resume.pdf --job "Senior Python Developer with 5+ years experience in Django, PostgreSQL, AWS. Required: Python, Django, REST APIs, Docker."
```

#### `--job-file PATH`
Load job description from a file.

**Example:**
```bash
resume-gen generate resume.pdf --job-file job_posting.txt
```

**job_posting.txt:**
```
Senior Python Developer
Tech Startup Inc.

We're seeking an experienced Python developer...
Requirements:
- 5+ years Python experience
- Django/Flask frameworks
- PostgreSQL, Redis
- AWS/Docker knowledge
```

#### `--job-url URL`
Fetch job description from URL.

**Example:**
```bash
resume-gen generate resume.pdf --job-url https://example.com/careers/senior-python-dev
```

**Note:** Requires internet connection and accessible URL

### Template Options

#### `-t, --template TEMPLATE`
Choose resume template.

**Options:**
- `modern` (default): Professional two-column design with color
- `ats`: ATS-friendly single-column format

**Examples:**
```bash
resume-gen generate resume.pdf -t modern
resume-gen generate resume.pdf --template ats
```

### Display Options

#### `-v, --verbose`
Enable verbose output with detailed progress.

**Example:**
```bash
resume-gen generate resume.pdf -v
```

**Output:**
```
[LOADING] Reading input files...
  ✓ resume.pdf (2,451 chars)
[EXTRACTING] Analyzing with Claude AI...
  ✓ Extracted 3 experiences, 12 skills
[OPTIMIZING] Applying X-Y-Z formula...
  ✓ Optimized 15 bullets (score: 0.85)
[GENERATING] Building LaTeX...
  ✓ Generated: output/john_doe_resume.tex
[COMPILING] Running pdflatex...
  ✓ Compiled: output/john_doe_resume.pdf

✓ Resume generated successfully!
  Output: output/john_doe_resume.pdf
  Optimization score: 0.85
  Keyword match: 72%
```

#### `-V, --version`
Show version and exit.

```bash
resume-gen --version
```

#### `--help`
Show help message and exit.

```bash
resume-gen --help
resume-gen generate --help
```

## Complete Examples

### Example 1: Basic Generation

```bash
resume-gen generate resume.pdf
```

**What happens:**
1. Extracts text from `resume.pdf`
2. Analyzes content with Claude AI
3. Optimizes bullet points
4. Generates modern template
5. Compiles to PDF
6. Saves to `./output/[name]_resume.pdf`

### Example 2: Job Tailoring

```bash
resume-gen generate resume.pdf \
  --job-file senior_python_dev.txt \
  --template ats \
  -o tailored_resume.pdf
```

**What happens:**
1. Loads resume data
2. Loads job description from file
3. Extracts profile
4. Optimizes content
5. **Tailors to job requirements**
6. Uses ATS-friendly template
7. Saves to `tailored_resume.pdf`

### Example 3: Multiple Sources

```bash
resume-gen generate \
  resume.pdf \
  linkedin_profile.txt \
  projects.md \
  --job-url https://example.com/job/senior-dev \
  -v
```

**What happens:**
1. Combines text from all sources
2. Fetches job description from URL
3. Extracts unified profile
4. Optimizes and tailors
5. Generates PDF
6. Shows verbose progress

### Example 4: LaTeX Only

```bash
resume-gen generate resume.pdf \
  --no-compile \
  -o resume.tex
```

**Use case:** Manual LaTeX editing before compilation

**Follow-up:**
```bash
pdflatex resume.tex
```

### Example 5: Directory Processing

```bash
resume-gen generate ./my_resume_data/ \
  --job "Full Stack Engineer with React and Node.js experience" \
  --template modern \
  -o fullstack_resume.pdf
```

**Directory structure:**
```
my_resume_data/
├── resume.pdf
├── cover_letter.txt
├── projects.md
└── certifications.txt
```

### Example 6: Batch Processing

```bash
for resume in resumes/*.pdf; do
  name=$(basename "$resume" .pdf)
  resume-gen generate "$resume" -o "output/${name}_generated.pdf"
done
```

## Configuration via Environment Variables

All settings can be configured via environment variables with `RESUME_GEN_` prefix:

```bash
export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."
export RESUME_GEN_CLAUDE_MODEL="claude-sonnet-4-20250514"
export RESUME_GEN_OUTPUT_DIR="./output"
export RESUME_GEN_DEFAULT_TEMPLATE="modern"
export RESUME_GEN_COMPILE_PDF="true"
export RESUME_GEN_VERBOSE="false"
```

Or create `.env` file:

```bash
RESUME_GEN_ANTHROPIC_API_KEY=sk-ant-...
RESUME_GEN_CLAUDE_MODEL=claude-sonnet-4-20250514
RESUME_GEN_OUTPUT_DIR=./output
RESUME_GEN_DEFAULT_TEMPLATE=modern
RESUME_GEN_PRIMARY_COLOR=#2C3E50
RESUME_GEN_COMPILE_PDF=true
```

See [CONFIGURATION.md](./CONFIGURATION.md) for all options.

## Output Files

### Default Output Location

```
./output/[firstname]_[lastname]_resume.pdf
```

### With Job Tailoring

```
./output/[firstname]_[lastname]_[job_title]_resume.pdf
```

### LaTeX Source Files

When PDF compilation is enabled, LaTeX source is kept:

```
./output/[firstname]_[lastname]_resume.tex
./output/[firstname]_[lastname]_resume.pdf
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | File not found |
| 3 | API error |
| 4 | Compilation error |

**Example:**
```bash
resume-gen generate resume.pdf
if [ $? -eq 0 ]; then
  echo "Success!"
else
  echo "Failed with code $?"
fi
```

## Troubleshooting

### Issue: API Key Error

**Error:**
```
Error: anthropic_api_key is required
```

**Solution:**
```bash
export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."
resume-gen generate resume.pdf
```

### Issue: pdflatex Not Found

**Error:**
```
Error: pdflatex command not found
```

**Solution:**
```bash
sudo apt-get install texlive-latex-base texlive-fonts-recommended
```

Or skip PDF compilation:
```bash
resume-gen generate resume.pdf --no-compile
```

### Issue: PDF Extraction Failed

**Error:**
```
Error: Unable to extract text from PDF
```

**Causes:**
- Scanned PDF (image-based, not text)
- Encrypted/password-protected PDF
- Corrupted file

**Solution:**
- Use OCR to convert scanned PDFs
- Remove password protection
- Use text/markdown input instead

### Issue: File Not Found

**Error:**
```
Error: resume.pdf not found
```

**Solution:**
```bash
ls -la resume.pdf
resume-gen generate /full/path/to/resume.pdf
```

### Issue: API Rate Limit

**Error:**
```
Error: Rate limit exceeded
```

**Solution:**
- Wait and retry
- Reduce concurrent requests
- Check API usage dashboard

### Issue: LaTeX Compilation Failed

**Error:**
```
Error: PDF compilation failed
```

**Solution:**
```bash
resume-gen generate resume.pdf --no-compile -o resume.tex
pdflatex resume.tex
```

Check LaTeX logs for specific errors.

## Performance Tips

1. **Use directories for multiple files** (faster than multiple CLI calls)
2. **Enable caching** for repeated processing
3. **Use `--no-compile`** for faster iteration during development
4. **Batch process** with shell scripts for multiple resumes
5. **Monitor API usage** to stay within rate limits

## Shell Completion

### Bash

```bash
eval "$(_RESUME_GEN_COMPLETE=bash_source resume-gen)"
```

Add to `~/.bashrc` for persistence.

### Zsh

```bash
eval "$(_RESUME_GEN_COMPLETE=zsh_source resume-gen)"
```

Add to `~/.zshrc` for persistence.

### Fish

```bash
eval (env _RESUME_GEN_COMPLETE=fish_source resume-gen)
```

## Advanced Usage

### Custom Configuration File

```bash
resume-gen generate resume.pdf --config custom_config.env
```

### Debug Mode

```bash
RESUME_GEN_VERBOSE=true RESUME_GEN_LOG_LEVEL=debug resume-gen generate resume.pdf -v
```

### Programmatic Invocation

```python
import subprocess

result = subprocess.run(
    ["resume-gen", "generate", "resume.pdf", "-o", "output.pdf"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("Success!")
    print(result.stdout)
else:
    print("Failed!")
    print(result.stderr)
```

## Integration Examples

### Git Hook (Pre-commit)

```bash
#!/bin/bash
if [ -f "resume.pdf" ]; then
  resume-gen generate resume.pdf -o dist/resume.pdf
fi
```

### CI/CD (GitHub Actions)

```yaml
- name: Generate Resume
  run: |
    pip install resume-generator
    resume-gen generate resume.pdf -o dist/resume.pdf
  env:
    RESUME_GEN_ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Makefile

```makefile
.PHONY: resume
resume:
	resume-gen generate resume.pdf -o dist/resume.pdf

.PHONY: tailored
tailored:
	resume-gen generate resume.pdf --job-file job.txt -o dist/tailored.pdf
```

## Best Practices

1. **Keep source files organized** in a dedicated directory
2. **Version control your source data** but not generated PDFs
3. **Use job tailoring** for each application
4. **Review generated content** before sending
5. **Keep LaTeX sources** for manual fine-tuning
6. **Use ATS template** for online applications
7. **Use modern template** for direct submissions
8. **Set up environment variables** in your shell profile

## Next Steps

- Read [API_REFERENCE.md](./API_REFERENCE.md) for programmatic usage
- Check [CONFIGURATION.md](./CONFIGURATION.md) for all settings
- Review [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- Explore templates in `src/resume_generator/generation/templates/`

## Support

For CLI issues:
- GitHub Issues: https://github.com/sebastian/resume-generator/issues
- Documentation: https://github.com/sebastian/resume-generator/docs

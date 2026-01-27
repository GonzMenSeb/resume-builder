# Configuration Reference

## Overview

Resume Generator uses Pydantic Settings for configuration management. Settings can be configured via:

1. Environment variables (with `RESUME_GEN_` prefix)
2. `.env` file
3. Programmatic configuration
4. Default values

## Configuration Hierarchy

Settings are loaded in this order (later overrides earlier):

```
Default Values → .env File → Environment Variables → Programmatic Config
```

## Quick Start

### Using .env File

Create `.env` in your project root:

```bash
RESUME_GEN_ANTHROPIC_API_KEY=sk-ant-...
RESUME_GEN_CLAUDE_MODEL=claude-sonnet-4-20250514
RESUME_GEN_DEFAULT_TEMPLATE=modern
RESUME_GEN_OUTPUT_DIR=./output
RESUME_GEN_COMPILE_PDF=true
```

### Using Environment Variables

```bash
export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."
export RESUME_GEN_CLAUDE_MODEL="claude-sonnet-4-20250514"
```

### Programmatic Configuration

```python
from resume_generator.config import Settings, get_settings

settings = get_settings()
settings.anthropic_api_key = "sk-ant-..."
settings.output_dir = Path("./custom_output")
```

## Configuration Sections

### API Configuration

Settings for Claude AI API interaction.

#### `ANTHROPIC_API_KEY`

**Type:** `str` (required)
**Default:** None
**Description:** Your Anthropic API key for Claude access

**Environment Variable:**
```bash
RESUME_GEN_ANTHROPIC_API_KEY=sk-ant-api01-...
```

**Security:** Never commit API keys to version control

#### `CLAUDE_MODEL`

**Type:** `str`
**Default:** `claude-sonnet-4-20250514`
**Description:** Claude model ID to use

**Options:**
- `claude-sonnet-4-20250514` (recommended, balanced)
- `claude-opus-4-20250514` (highest quality, slower)
- `claude-3-5-sonnet-20241022` (older, faster)

**Environment Variable:**
```bash
RESUME_GEN_CLAUDE_MODEL=claude-sonnet-4-20250514
```

**Note:** Opus provides highest quality but costs more and is slower

#### `MAX_TOKENS`

**Type:** `int`
**Default:** `4096`
**Range:** `1024-8192`
**Description:** Maximum tokens for Claude responses

**Environment Variable:**
```bash
RESUME_GEN_MAX_TOKENS=4096
```

**Trade-offs:**
- Higher = More detailed responses, higher cost
- Lower = Faster, cheaper, may truncate content

#### `CLAUDE_CLI_TIMEOUT`

**Type:** `int`
**Default:** `3600`
**Range:** `60-7200` (seconds)
**Description:** Timeout for Claude CLI subprocess invocations

**Environment Variable:**
```bash
RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600
```

**Recommendations:**
- `1800` for simple operations
- `3600` for normal usage (default)
- `7200` for complex multi-step operations

#### `CLAUDE_CLI_VERBOSE`

**Type:** `bool`
**Default:** `false`
**Description:** Enable verbose output during Claude CLI invocations

**Environment Variable:**
```bash
RESUME_GEN_CLAUDE_CLI_VERBOSE=true
```

### Path Configuration

File system paths and directories.

#### `OUTPUT_DIR`

**Type:** `Path`
**Default:** `./output`
**Description:** Output directory for generated resumes

**Environment Variable:**
```bash
RESUME_GEN_OUTPUT_DIR=/home/user/resumes/output
```

**Auto-created:** Yes, if it doesn't exist

#### `CACHE_DIR`

**Type:** `Path`
**Default:** `./.resume_cache`
**Description:** Cache directory for temporary data

**Environment Variable:**
```bash
RESUME_GEN_CACHE_DIR=/tmp/resume_cache
```

**Contents:**
- Cached API responses
- Temporary compilation files
- Processed data

**Clean-up:** Safe to delete, will be recreated

### Template & Design Configuration

Visual appearance and template settings.

#### `DEFAULT_TEMPLATE`

**Type:** `ResumeTemplate`
**Default:** `modern`
**Options:** `modern`, `ats`
**Description:** Default resume template

**Environment Variable:**
```bash
RESUME_GEN_DEFAULT_TEMPLATE=modern
```

**Templates:**

| Template | Description | Use Case |
|----------|-------------|----------|
| `modern` | Two-column, color accents, professional | Direct submissions, email |
| `ats` | Single-column, simple, machine-readable | Online application systems |

#### `PRIMARY_COLOR`

**Type:** `str`
**Default:** `#2C3E50`
**Format:** Hex color code
**Description:** Primary color for headers and accents

**Environment Variable:**
```bash
RESUME_GEN_PRIMARY_COLOR=#1E3A8A
```

**Examples:**
- `#2C3E50` - Dark blue-gray (default, professional)
- `#1E3A8A` - Deep blue (tech)
- `#7C3AED` - Purple (creative)
- `#DC2626` - Red (bold)

**ATS Note:** Color is ignored in ATS template

#### `SECONDARY_COLOR`

**Type:** `str`
**Default:** `#3498DB`
**Format:** Hex color code
**Description:** Secondary color for links and highlights

**Environment Variable:**
```bash
RESUME_GEN_SECONDARY_COLOR=#3B82F6
```

#### `FONT_NAME_SIZE`

**Type:** `int`
**Default:** `20`
**Range:** `18-24` (points)
**Description:** Font size for candidate name

**Environment Variable:**
```bash
RESUME_GEN_FONT_NAME_SIZE=22
```

**Guidelines:**
- `18-19` - Subtle, more space for content
- `20-21` - Balanced (recommended)
- `22-24` - Bold, eye-catching

#### `FONT_HEADER_SIZE`

**Type:** `int`
**Default:** `14`
**Range:** `12-16` (points)
**Description:** Font size for section headers

**Environment Variable:**
```bash
RESUME_GEN_FONT_HEADER_SIZE=14
```

#### `FONT_BODY_SIZE`

**Type:** `int`
**Default:** `11`
**Range:** `10-12` (points)
**Description:** Font size for body text

**Environment Variable:**
```bash
RESUME_GEN_FONT_BODY_SIZE=11
```

**Recommendations:**
- `10` - Fit more content, may be hard to read
- `11` - Standard, optimal (default)
- `12` - Very readable, less content fits

#### `MARGIN_INCHES`

**Type:** `float`
**Default:** `0.75`
**Range:** `0.5-1.0` (inches)
**Description:** Page margins (all sides)

**Environment Variable:**
```bash
RESUME_GEN_MARGIN_INCHES=0.75
```

**Trade-offs:**
- `0.5` - More content space, cramped appearance
- `0.75` - Balanced (default)
- `1.0` - Clean, lots of whitespace, less content

### Content Optimization

Settings for resume content optimization.

#### `MIN_BULLETS_PER_JOB`

**Type:** `int`
**Default:** `3`
**Range:** `2-5`
**Description:** Minimum bullet points per job

**Environment Variable:**
```bash
RESUME_GEN_MIN_BULLETS_PER_JOB=3
```

#### `MAX_BULLETS_PER_JOB`

**Type:** `int`
**Default:** `5`
**Range:** `3-7`
**Description:** Maximum bullet points per job

**Environment Variable:**
```bash
RESUME_GEN_MAX_BULLETS_PER_JOB=5
```

**Recommendations:**
- Recent roles: 4-6 bullets
- Older roles: 2-3 bullets
- Most relevant role: Up to 7 bullets

#### `SUMMARY_MIN_WORDS`

**Type:** `int`
**Default:** `50`
**Range:** `30-80`
**Description:** Minimum words in professional summary

**Environment Variable:**
```bash
RESUME_GEN_SUMMARY_MIN_WORDS=50
```

#### `SUMMARY_MAX_WORDS`

**Type:** `int`
**Default:** `100`
**Range:** `80-150`
**Description:** Maximum words in professional summary

**Environment Variable:**
```bash
RESUME_GEN_SUMMARY_MAX_WORDS=100
```

**Guidelines:**
- 50-75 words: Concise, punchy
- 75-100 words: Standard (default)
- 100-150 words: Detailed, senior roles

#### `TARGET_KEYWORD_MATCH_RATE`

**Type:** `float`
**Default:** `0.70`
**Range:** `0.50-0.90`
**Description:** Target keyword match rate for job tailoring

**Environment Variable:**
```bash
RESUME_GEN_TARGET_KEYWORD_MATCH_RATE=0.70
```

**Interpretation:**
- `0.50-0.60` - Light tailoring
- `0.65-0.75` - Balanced (recommended)
- `0.80-0.90` - Heavy tailoring (may feel artificial)

#### `TAILORING_CUSTOMIZATION_RATE`

**Type:** `float`
**Default:** `0.50`
**Range:** `0.30-0.70`
**Description:** How much to customize content for job

**Environment Variable:**
```bash
RESUME_GEN_TAILORING_CUSTOMIZATION_RATE=0.50
```

**Interpretation:**
- `0.30` - Minor adjustments
- `0.50` - Moderate customization (default)
- `0.70` - Significant rewriting

### Pipeline Options

Control pipeline behavior and execution.

#### `ENABLE_JOB_TAILORING`

**Type:** `bool`
**Default:** `true`
**Description:** Enable job-specific optimization

**Environment Variable:**
```bash
RESUME_GEN_ENABLE_JOB_TAILORING=true
```

**When False:**
- Skips tailoring stage even if job is provided
- Faster execution
- Generic resume output

#### `COMPILE_PDF`

**Type:** `bool`
**Default:** `true`
**Description:** Compile LaTeX to PDF

**Environment Variable:**
```bash
RESUME_GEN_COMPILE_PDF=true
```

**When False:**
- Outputs .tex file only
- No PDF generation
- Requires `pdflatex` for manual compilation

#### `KEEP_LATEX_SOURCE`

**Type:** `bool`
**Default:** `true`
**Description:** Keep generated .tex file after PDF compilation

**Environment Variable:**
```bash
RESUME_GEN_KEEP_LATEX_SOURCE=true
```

**When False:**
- Deletes .tex file after compilation
- Only keeps PDF
- Saves disk space

#### `VERBOSE`

**Type:** `bool`
**Default:** `false`
**Description:** Enable verbose output

**Environment Variable:**
```bash
RESUME_GEN_VERBOSE=true
```

**When True:**
- Detailed progress messages
- Stage timing information
- Debug information

## Complete Configuration Example

### Production .env

```bash
# API Configuration
RESUME_GEN_CLAUDE_MODEL=sonnet
RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600
RESUME_GEN_CLAUDE_CLI_VERBOSE=false

# Paths
RESUME_GEN_OUTPUT_DIR=./output
RESUME_GEN_CACHE_DIR=./.resume_cache

# Template & Design
RESUME_GEN_DEFAULT_TEMPLATE=modern
RESUME_GEN_PRIMARY_COLOR=#2C3E50
RESUME_GEN_SECONDARY_COLOR=#3498DB
RESUME_GEN_FONT_NAME_SIZE=20
RESUME_GEN_FONT_HEADER_SIZE=14
RESUME_GEN_FONT_BODY_SIZE=11
RESUME_GEN_MARGIN_INCHES=0.75

# Content Optimization
RESUME_GEN_MIN_BULLETS_PER_JOB=3
RESUME_GEN_MAX_BULLETS_PER_JOB=5
RESUME_GEN_SUMMARY_MIN_WORDS=50
RESUME_GEN_SUMMARY_MAX_WORDS=100
RESUME_GEN_TARGET_KEYWORD_MATCH_RATE=0.70
RESUME_GEN_TAILORING_CUSTOMIZATION_RATE=0.50

# Pipeline Options
RESUME_GEN_ENABLE_JOB_TAILORING=true
RESUME_GEN_COMPILE_PDF=true
RESUME_GEN_KEEP_LATEX_SOURCE=true
RESUME_GEN_VERBOSE=false
```

### Programmatic Configuration

```python
from pathlib import Path
from resume_generator.config import Settings, ResumeTemplate

settings = Settings(
    # API
    claude_model=ClaudeModel.SONNET,
    claude_cli_timeout=3600,
    claude_cli_verbose=False,

    # Paths
    output_dir=Path("./output"),
    cache_dir=Path("./.resume_cache"),

    # Template
    default_template=ResumeTemplate.MODERN,
    primary_color="#2C3E50",
    secondary_color="#3498DB",
    font_name_size=20,
    font_header_size=14,
    font_body_size=11,
    margin_inches=0.75,

    # Content
    min_bullets_per_job=3,
    max_bullets_per_job=5,
    summary_min_words=50,
    summary_max_words=100,
    target_keyword_match_rate=0.70,
    tailoring_customization_rate=0.50,

    # Pipeline
    enable_job_tailoring=True,
    compile_pdf=True,
    keep_latex_source=True,
    verbose=False,
)
```

## Configuration Profiles

### Profile: Quick Resume

Fast generation with minimal AI processing.

```bash
RESUME_GEN_CLAUDE_MODEL=haiku
RESUME_GEN_CLAUDE_CLI_TIMEOUT=1800
RESUME_GEN_ENABLE_JOB_TAILORING=false
RESUME_GEN_MIN_BULLETS_PER_JOB=2
RESUME_GEN_MAX_BULLETS_PER_JOB=4
```

### Profile: High Quality

Maximum quality with detailed optimization.

```bash
RESUME_GEN_CLAUDE_MODEL=opus
RESUME_GEN_CLAUDE_CLI_TIMEOUT=7200
RESUME_GEN_TARGET_KEYWORD_MATCH_RATE=0.80
RESUME_GEN_TAILORING_CUSTOMIZATION_RATE=0.65
RESUME_GEN_MAX_BULLETS_PER_JOB=6
```

### Profile: ATS Optimized

Focus on ATS compatibility.

```bash
RESUME_GEN_DEFAULT_TEMPLATE=ats
RESUME_GEN_TARGET_KEYWORD_MATCH_RATE=0.85
RESUME_GEN_TAILORING_CUSTOMIZATION_RATE=0.70
RESUME_GEN_FONT_BODY_SIZE=11
RESUME_GEN_MARGIN_INCHES=0.75
```

### Profile: Development

For testing and debugging.

```bash
RESUME_GEN_VERBOSE=true
RESUME_GEN_COMPILE_PDF=false
RESUME_GEN_KEEP_LATEX_SOURCE=true
RESUME_GEN_CLAUDE_CLI_TIMEOUT=7200
RESUME_GEN_CLAUDE_CLI_VERBOSE=true
```

## Validation

Settings are validated on load. Invalid values raise errors:

```python
from resume_generator.config import Settings

try:
    settings = Settings(font_body_size=5)  # Too small
except ValueError as e:
    print(f"Invalid configuration: {e}")
```

## Environment Detection

Settings automatically detect the environment:

```python
from resume_generator.config import get_settings

settings = get_settings()

if settings.verbose:
    print("Verbose mode enabled")
```

## Best Practices

1. **Never commit API keys** to version control
2. **Use .env for local development** and environment variables for production
3. **Start with defaults** and adjust based on results
4. **Profile your configurations** for different use cases
5. **Document custom settings** in project README
6. **Validate settings** before production deployment
7. **Use ATS template** for online applications
8. **Monitor API usage** and costs

## Troubleshooting

### Settings Not Loading

**Check:**
1. `.env` file exists in working directory
2. Environment variables properly exported
3. Variable names include `RESUME_GEN_` prefix
4. No typos in variable names

### Invalid Values

**Error:**
```
ValidationError: font_body_size must be between 10 and 12
```

**Solution:**
Check allowed ranges in this documentation

### API Key Not Found

**Error:**
```
Error: anthropic_api_key is required
```

**Solution:**
```bash
export RESUME_GEN_ANTHROPIC_API_KEY="sk-ant-..."
```

## Related Documentation

- [CLI Guide](./CLI_GUIDE.md) - CLI usage with configuration
- [API Reference](./API_REFERENCE.md) - Programmatic configuration
- [Architecture](./ARCHITECTURE.md) - How configuration affects pipeline

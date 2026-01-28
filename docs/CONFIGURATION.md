# Configuration Reference

## Overview

Resume Generator uses a flexible configuration system with multiple sources. Settings can be configured via:

1. **YAML configuration file** (recommended for persistent settings)
2. **CLI options** (for per-execution overrides)
3. **Environment variables** (with `RESUME_GEN_` prefix)
4. **`.env` file**
5. **Programmatic configuration**

## Configuration Hierarchy

Settings are loaded in this order (later overrides earlier):

```
Default Values → .env File → Environment Variables → YAML Config → CLI Options
```

## Quick Start

### Using YAML Configuration File (Recommended)

Create a configuration file:

```bash
resume-gen init
```

This creates `resume-gen.yaml` in your current directory. Edit it:

```yaml
# resume-gen.yaml
max_pages: 1
max_bullet_words: 25
color_palette: burgundy
claude_model: sonnet
output_language: en
min_bullets_per_job: 3
max_bullets_per_job: 5
compile_pdf: true
```

**Config file search locations** (in order):
1. `./resume-gen.yaml`
2. `./.resume-gen.yaml`
3. `~/.resume-gen.yaml`
4. `~/.config/resume-gen/config.yaml`

**Use a specific config file:**
```bash
resume-gen generate ./data/ --config my-custom-config.yaml
```

**View current configuration:**
```bash
resume-gen config
```

### Using .env File

Create `.env` in your project root:

```bash
RESUME_GEN_CLAUDE_MODEL=sonnet
RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600
RESUME_GEN_DEFAULT_TEMPLATE=modern
RESUME_GEN_OUTPUT_DIR=./output
RESUME_GEN_COMPILE_PDF=true
```

### Using Environment Variables

```bash
export RESUME_GEN_CLAUDE_MODEL=sonnet
export RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600
```

### Programmatic Configuration

```python
from pathlib import Path
from resume_generator.config import Settings, get_settings, ClaudeModel, ColorPalette

# Load from default config file
settings = get_settings()

# Load from specific config file
settings = get_settings(config_path=Path("my-config.yaml"))

# Override settings
settings = settings.model_copy(update={
    "claude_model": ClaudeModel.SONNET,
    "color_palette": ColorPalette.BURGUNDY,
    "max_pages": 1,
})
```

## Configuration Sections

### Claude CLI Configuration

Settings for Claude CLI subprocess interaction.

#### `CLAUDE_MODEL`

**Type:** `str`
**Default:** `sonnet`
**Description:** Claude model to use via CLI

**Options:**
- `sonnet` (recommended, balanced)
- `opus` (highest quality, slower)
- `haiku` (fastest, lower quality)

**Environment Variable:**
```bash
RESUME_GEN_CLAUDE_MODEL=sonnet
```

**Note:** Requires Claude CLI to be installed and accessible in PATH

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

**YAML:**
```yaml
default_template: modern
```

**Environment Variable:**
```bash
RESUME_GEN_DEFAULT_TEMPLATE=modern
```

**Templates:**

| Template | Description | Use Case |
|----------|-------------|----------|
| `modern` | Two-column, color accents, professional | Direct submissions, email |
| `ats` | Single-column, simple, machine-readable | Online application systems |

#### `COLOR_PALETTE`

**Type:** `ColorPalette`
**Default:** `classic`
**Options:** `classic`, `burgundy`, `navy`, `forest`, `slate`, `charcoal`
**Description:** Predefined color scheme for resume styling

**YAML:**
```yaml
color_palette: burgundy
```

**CLI:**
```bash
resume-gen generate ./data/ --colors burgundy
```

**Environment Variable:**
```bash
RESUME_GEN_COLOR_PALETTE=burgundy
```

**Available Palettes:**

| Palette | Primary | Secondary | Best For |
|---------|---------|-----------|----------|
| `classic` | #2C3E50 (dark blue) | #3498DB (bright blue) | Traditional corporate |
| `burgundy` | #800020 (burgundy) | #4A4A4A (gray) | Elegant/executive |
| `navy` | #1B365D (navy) | #5B7C99 (slate blue) | Finance/legal |
| `forest` | #2D5A27 (forest) | #6B8E23 (olive) | Environmental/creative |
| `slate` | #4A5568 (slate) | #718096 (gray) | Modern minimalist |
| `charcoal` | #2D3748 (charcoal) | #4A5568 (slate) | Tech/startup |

**Note:** Color palette overrides `PRIMARY_COLOR` and `SECONDARY_COLOR` settings.

#### `PRIMARY_COLOR`

**Type:** `str`
**Default:** `#2C3E50`
**Format:** Hex color code
**Description:** Primary color for headers and accents (overridden by `color_palette`)

**YAML:**
```yaml
primary_color: "#1E3A8A"
```

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
**Description:** Secondary color for links and highlights (overridden by `color_palette`)

**YAML:**
```yaml
secondary_color: "#3B82F6"
```

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

#### `MAX_PAGES`

**Type:** `int`
**Default:** `1`
**Range:** `1-3`
**Description:** Maximum pages for the final resume. If the generated resume exceeds this limit, bullets will be automatically compacted.

**YAML:**
```yaml
max_pages: 1
```

**CLI:**
```bash
resume-gen generate ./data/ --max-pages 2
```

**Environment Variable:**
```bash
RESUME_GEN_MAX_PAGES=1
```

**Behavior:**
- When PDF exceeds `max_pages`, the pipeline automatically removes lower-priority bullets
- Compaction respects `min_bullets_per_job` setting
- Up to 5 compaction rounds are attempted

#### `MAX_BULLET_WORDS`

**Type:** `int`
**Default:** `25`
**Range:** `10-50`
**Description:** Maximum words per bullet point. Claude AI is instructed to keep bullets concise.

**YAML:**
```yaml
max_bullet_words: 25
```

**CLI:**
```bash
resume-gen generate ./data/ --max-bullet-words 20
```

**Environment Variable:**
```bash
RESUME_GEN_MAX_BULLET_WORDS=25
```

**Guidelines:**
- `10-15` words: Very concise, headline-style bullets
- `20-25` words: Standard, recommended (default)
- `30-50` words: Detailed, for complex achievements

#### `MIN_BULLETS_PER_JOB`

**Type:** `int`
**Default:** `3`
**Range:** `2-5`
**Description:** Minimum bullet points per job

**YAML:**
```yaml
min_bullets_per_job: 3
```

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

### YAML Configuration (Recommended)

Create `resume-gen.yaml`:

```yaml
# Resume Generator Configuration

# === Output Constraints ===
max_pages: 1
max_bullet_words: 25
compile_pdf: true
keep_latex_source: true

# === AI Settings ===
claude_model: sonnet
claude_cli_timeout: 3600

# === Design ===
color_palette: classic
# Or use custom colors:
# primary_color: "#2C3E50"
# secondary_color: "#3498DB"

# === Content Optimization ===
min_bullets_per_job: 3
max_bullets_per_job: 5
summary_min_words: 50
summary_max_words: 100
target_keyword_match_rate: 0.70

# === Language ===
output_language: en

# === Paths ===
output_dir: ./output
cache_dir: ./.resume_cache

# === Pipeline ===
enable_job_tailoring: true
verbose: false
```

### Production .env

```bash
# Claude CLI Configuration
RESUME_GEN_CLAUDE_MODEL=sonnet
RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600
RESUME_GEN_CLAUDE_CLI_VERBOSE=false

# Output Constraints
RESUME_GEN_MAX_PAGES=1
RESUME_GEN_MAX_BULLET_WORDS=25

# Design
RESUME_GEN_COLOR_PALETTE=classic

# Paths
RESUME_GEN_OUTPUT_DIR=./output
RESUME_GEN_CACHE_DIR=./.resume_cache

# Content Optimization
RESUME_GEN_MIN_BULLETS_PER_JOB=3
RESUME_GEN_MAX_BULLETS_PER_JOB=5

# Pipeline Options
RESUME_GEN_COMPILE_PDF=true
RESUME_GEN_VERBOSE=false
```

### Programmatic Configuration

```python
from pathlib import Path
from resume_generator.config import (
    Settings, ResumeTemplate, ClaudeModel, ColorPalette, get_settings
)

# Load from YAML file
settings = get_settings(config_path=Path("my-config.yaml"))

# Or create directly
settings = Settings(
    # Output Constraints
    max_pages=1,
    max_bullet_words=25,

    # Claude CLI
    claude_model=ClaudeModel.SONNET,
    claude_cli_timeout=3600,

    # Design
    color_palette=ColorPalette.BURGUNDY,

    # Paths
    output_dir=Path("./output"),
    cache_dir=Path("./.resume_cache"),

    # Content
    min_bullets_per_job=3,
    max_bullets_per_job=5,

    # Pipeline
    enable_job_tailoring=True,
    compile_pdf=True,
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

### Claude CLI Not Found

**Error:**
```
Error: Claude CLI not available. Please install Claude CLI.
```

**Solution:**
Install Claude CLI from https://github.com/anthropics/claude-code

```bash
# macOS/Linux
brew install anthropic-cli

# Verify installation
claude --version
```

## Related Documentation

- [CLI Guide](./CLI_GUIDE.md) - CLI usage with configuration
- [API Reference](./API_REFERENCE.md) - Programmatic configuration
- [Architecture](./ARCHITECTURE.md) - How configuration affects pipeline

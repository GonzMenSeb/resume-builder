"""Configuration and settings for the resume generator."""

from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_FILE_NAME = "resume-gen.yaml"
CONFIG_SEARCH_PATHS = [
    Path.cwd() / CONFIG_FILE_NAME,
    Path.cwd() / f".{CONFIG_FILE_NAME}",
    Path.home() / f".{CONFIG_FILE_NAME}",
    Path.home() / ".config" / "resume-gen" / "config.yaml",
]


class ResumeTemplate(str, Enum):
    """Available resume templates."""

    MODERN = "modern"
    ATS = "ats"


class ColorPalette(str, Enum):
    """Predefined color palettes for resume styling."""

    CLASSIC = "classic"
    BURGUNDY = "burgundy"
    NAVY = "navy"
    FOREST = "forest"
    SLATE = "slate"
    CHARCOAL = "charcoal"


COLOR_PALETTE_VALUES: dict[ColorPalette, tuple[str, str]] = {
    ColorPalette.CLASSIC: ("#2C3E50", "#3498DB"),
    ColorPalette.BURGUNDY: ("#800020", "#4A4A4A"),
    ColorPalette.NAVY: ("#1B365D", "#5B7C99"),
    ColorPalette.FOREST: ("#2D5A27", "#6B8E23"),
    ColorPalette.SLATE: ("#4A5568", "#718096"),
    ColorPalette.CHARCOAL: ("#2D3748", "#4A5568"),
}


class ResumeLanguage(str, Enum):
    """Supported output languages for resume generation."""

    EN = "en"
    ES = "es"
    FR = "fr"
    DE = "de"
    PT = "pt"
    IT = "it"
    ZH = "zh"
    JA = "ja"
    KO = "ko"
    AR = "ar"
    NL = "nl"
    RU = "ru"
    PL = "pl"


class ClaudeModel(str, Enum):
    """Supported Claude models for CLI invocation."""

    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"


class TierGrade(str, Enum):
    """Valid tier grades for adversarial refinement."""

    S_PLUS = "S+"
    S = "S"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D = "D"
    F = "F"


TIER_GRADE_ORDER: dict[TierGrade, int] = {
    TierGrade.S_PLUS: 13,
    TierGrade.S: 12,
    TierGrade.A_PLUS: 11,
    TierGrade.A: 10,
    TierGrade.A_MINUS: 9,
    TierGrade.B_PLUS: 8,
    TierGrade.B: 7,
    TierGrade.B_MINUS: 6,
    TierGrade.C_PLUS: 5,
    TierGrade.C: 4,
    TierGrade.C_MINUS: 3,
    TierGrade.D: 2,
    TierGrade.F: 1,
}


def tier_meets_target(current: TierGrade, target: TierGrade) -> bool:
    """Check if current grade meets or exceeds target grade."""
    return TIER_GRADE_ORDER[current] >= TIER_GRADE_ORDER[target]


def parse_tier_grade(value: str) -> TierGrade | None:
    """Parse a string into a TierGrade, returning None if invalid."""
    if not value:
        return None
    normalized = value.strip().upper().replace(" ", "")
    for grade in TierGrade:
        if grade.value.upper().replace("+", "PLUS").replace("-", "MINUS") == normalized.replace(
            "+", "PLUS"
        ).replace("-", "MINUS"):
            return grade
        if grade.value.upper() == normalized:
            return grade
    return None


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="RESUME_GEN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    claude_model: ClaudeModel = Field(
        default=ClaudeModel.SONNET,
        description="Claude model to use for AI operations",
    )
    claude_cli_timeout: int = Field(
        default=3600,
        ge=60,
        le=7200,
        description="Timeout in seconds for Claude CLI invocations",
    )
    # Path Configuration
    input_dir: Path | None = Field(
        default=None,
        description="Default input directory for resume data (used when no inputs provided)",
    )
    output_dir: Path = Field(
        default=Path("./output"),
        description="Default output directory for generated resumes",
    )
    templates_dir: Path = Field(
        default=Path(__file__).parent / "generation" / "templates",
        description="Directory containing LaTeX templates",
    )
    cache_dir: Path = Field(
        default=Path("./.resume_cache"),
        description="Cache directory for intermediate files",
    )
    target_job_dir: Path | None = Field(
        default=None,
        description="Default directory for target job description files",
    )

    # Template & Design Configuration (research-backed defaults)
    default_template: ResumeTemplate = Field(
        default=ResumeTemplate.MODERN,
        description="Default resume template",
    )
    color_palette: ColorPalette = Field(
        default=ColorPalette.CLASSIC,
        description="Color palette for resume styling",
    )
    primary_color: str = Field(
        default="#2C3E50",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Primary color (hex) - overridden by color_palette if set",
    )
    secondary_color: str = Field(
        default="#3498DB",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Secondary color (hex) - overridden by color_palette if set",
    )
    font_name_size: int = Field(
        default=20,
        ge=18,
        le=24,
        description="Name font size in points",
    )
    font_header_size: int = Field(
        default=14,
        ge=12,
        le=16,
        description="Section header font size in points",
    )
    font_body_size: int = Field(
        default=11,
        ge=10,
        le=12,
        description="Body text font size in points",
    )
    margin_inches: Annotated[float, Field(ge=0.5, le=1.0)] = 0.75

    # Content Optimization (research-backed defaults)
    max_pages: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Maximum pages for the final resume",
    )
    max_bullet_words: int = Field(
        default=25,
        ge=10,
        le=50,
        description="Maximum words per bullet point",
    )
    min_bullets_per_job: int = Field(
        default=3,
        ge=2,
        le=5,
        description="Minimum bullet points per job position",
    )
    max_bullets_per_job: int = Field(
        default=5,
        ge=3,
        le=7,
        description="Maximum bullet points per job position",
    )
    summary_min_words: int = Field(
        default=50,
        ge=30,
        le=80,
        description="Minimum words in professional summary",
    )
    summary_max_words: int = Field(
        default=100,
        ge=80,
        le=150,
        description="Maximum words in professional summary",
    )
    target_keyword_match_rate: float = Field(
        default=0.70,
        ge=0.5,
        le=0.9,
        description="Target keyword match rate for job tailoring (65-80% recommended)",
    )
    tailoring_customization_rate: float = Field(
        default=0.50,
        ge=0.3,
        le=0.7,
        description="How much to customize resume for job (40-60% recommended)",
    )

    # Pipeline Options
    enable_job_tailoring: bool = Field(
        default=True,
        description="Enable job-specific resume optimization",
    )
    compile_pdf: bool = Field(
        default=True,
        description="Compile LaTeX to PDF after generation",
    )
    keep_latex_source: bool = Field(
        default=True,
        description="Keep the generated LaTeX source file",
    )
    output_language: ResumeLanguage = Field(
        default=ResumeLanguage.EN,
        description="Language for the generated resume content",
    )

    log_level: str = Field(
        default="INFO",
        description="Log level for pipeline file logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.strip().upper()
        if normalized not in valid:
            raise ValueError(f"Invalid log_level '{v}'. Valid values: {', '.join(sorted(valid))}")
        return normalized

    target_tier: str | None = Field(
        default=None,
        description="Target tier grade for adversarial refinement (S+, S, A+, A, A-, B+, B, etc). If set, enables the refinement loop.",
    )
    max_refinement_iterations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum iterations for adversarial refinement loop",
    )
    refinement_research_dir: Path = Field(
        default=Path(__file__).parent.parent.parent / "docs" / "research-results" / "tex",
        description="Directory containing research documents for critique criteria",
    )

    @field_validator("target_tier", mode="before")
    @classmethod
    def validate_target_tier(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        parsed = parse_tier_grade(v)
        if parsed is None:
            valid_grades = ", ".join(g.value for g in TierGrade)
            raise ValueError(f"Invalid target_tier '{v}'. Valid values: {valid_grades}")
        return parsed.value

    def get_target_tier_grade(self) -> TierGrade | None:
        """Get the target tier as a TierGrade enum, or None if not set."""
        if self.target_tier is None:
            return None
        return parse_tier_grade(self.target_tier)

    @field_validator(
        "input_dir",
        "output_dir",
        "templates_dir",
        "cache_dir",
        "target_job_dir",
        "refinement_research_dir",
        mode="before",
    )
    @classmethod
    def ensure_path(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        return Path(v) if isinstance(v, str) else v

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_template_path(self, template: ResumeTemplate | None = None) -> Path:
        """Get the path to a specific template file."""
        t = template or self.default_template
        return self.templates_dir / f"{t.value}.tex"

    def get_effective_colors(self) -> tuple[str, str]:
        """Get effective primary and secondary colors.

        If custom colors differ from defaults (indicating user override),
        those are used. Otherwise, the color palette is applied.
        """
        default_primary = "#2C3E50"
        default_secondary = "#3498DB"
        if self.primary_color != default_primary or self.secondary_color != default_secondary:
            return (self.primary_color, self.secondary_color)
        return COLOR_PALETTE_VALUES[self.color_palette]


def find_config_file() -> Path | None:
    """Find the first existing config file from search paths."""
    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return path
    return None


def load_yaml_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file."""
    path = config_path or find_config_file()
    if path is None or not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def get_settings(config_path: Path | None = None) -> Settings:
    """Factory function to get settings instance with YAML config support."""
    yaml_config = load_yaml_config(config_path)
    return Settings(**yaml_config)


def get_default_config_template() -> str:
    """Generate a default YAML configuration template with comments."""
    return """\
# Resume Generator Configuration
# Place this file as resume-gen.yaml in your project directory
# or as ~/.resume-gen.yaml for global settings

# === Output Settings ===
max_pages: 1              # Maximum pages (1-3)
max_bullet_words: 25      # Max words per bullet point (10-50)
compile_pdf: true         # Generate PDF (false = LaTeX only)
keep_latex_source: true   # Keep .tex file after compilation

# === AI Settings ===
claude_model: sonnet      # Model: sonnet, opus, haiku

# === Design Settings ===
color_palette: classic    # Palette: classic, burgundy, navy, forest, slate, charcoal
# Or specify custom colors (overrides palette):
# primary_color: "#2C3E50"
# secondary_color: "#3498DB"

# === Content Settings ===
min_bullets_per_job: 3    # Minimum bullets per job (2-5)
max_bullets_per_job: 5    # Maximum bullets per job (3-7)
summary_min_words: 50     # Min words in summary (30-80)
summary_max_words: 100    # Max words in summary (80-150)

# === Language ===
output_language: en       # Language: en, es, fr, de, pt, it, zh, ja, ko, ar, nl, ru, pl

# === Paths (optional) ===
# input_dir: ./resume_data    # Default input directory (allows running just 'resume-gen generate')
# output_dir: ./output
# cache_dir: ./.resume_cache

# === Advanced ===
# target_keyword_match_rate: 0.70
# tailoring_customization_rate: 0.50
# enable_job_tailoring: true
# === Logging ===
# log_level: INFO            # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL

# === Adversarial Refinement ===
# target_tier: S              # Target grade (S+, S, A+, A, A-, B+, B, etc). If set, enables refinement loop.
# max_refinement_iterations: 5  # Max iterations for refinement (1-10)
"""

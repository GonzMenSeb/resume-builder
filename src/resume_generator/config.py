"""Configuration and settings for the resume generator."""

from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ResumeTemplate(str, Enum):
    """Available resume templates."""

    MODERN = "modern"
    ATS = "ats"


class ClaudeModel(str, Enum):
    """Supported Claude models for CLI invocation."""

    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="RESUME_GEN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    anthropic_api_key: SecretStr = Field(
        default=...,
        description="Anthropic API key for Claude",
    )
    claude_model: ClaudeModel = Field(
        default=ClaudeModel.SONNET,
        description="Claude model to use for AI operations",
    )
    max_tokens: int = Field(
        default=4096,
        ge=256,
        le=8192,
        description="Maximum tokens for Claude responses",
    )
    api_timeout: float = Field(
        default=120.0,
        ge=10.0,
        le=600.0,
        description="API request timeout in seconds",
    )
    api_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls",
    )

    # Path Configuration
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

    # Template & Design Configuration (research-backed defaults)
    default_template: ResumeTemplate = Field(
        default=ResumeTemplate.MODERN,
        description="Default resume template",
    )
    primary_color: str = Field(
        default="#2C3E50",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Primary color (hex) for resume styling",
    )
    secondary_color: str = Field(
        default="#3498DB",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Secondary color (hex) for accents",
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
    verbose: bool = Field(
        default=False,
        description="Enable verbose output for debugging",
    )

    @field_validator("output_dir", "templates_dir", "cache_dir", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        return Path(v) if isinstance(v, str) else v

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_template_path(self, template: ResumeTemplate | None = None) -> Path:
        """Get the path to a specific template file."""
        t = template or self.default_template
        return self.templates_dir / f"{t.value}.tex"


def get_settings() -> Settings:
    """Factory function to get settings instance."""
    return Settings()

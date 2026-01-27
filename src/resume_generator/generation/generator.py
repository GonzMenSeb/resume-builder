"""LaTeX generator for converting ResumeDocument to LaTeX source."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..config import ResumeTemplate, Settings

TEMPLATES_DIR = Path(__file__).parent / "templates"

if TYPE_CHECKING:
    from ..models.resume import ResumeDocument


_BACKSLASH_PLACEHOLDER = "\x00BACKSLASH\x00"
_TILDE_PLACEHOLDER = "\x00TILDE\x00"
_CARET_PLACEHOLDER = "\x00CARET\x00"

LATEX_SPECIAL_CHARS: dict[str, str] = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
    "|": r"\textbar{}",
}

UNICODE_REPLACEMENTS: dict[str, str] = {
    "\u2018": "`",
    "\u2019": "'",
    "\u201c": "``",
    "\u201d": "''",
    "\u2013": "--",
    "\u2014": "---",
    "\u2026": r"\ldots{}",
    "\u00a0": "~",
    "\u00b0": r"\textdegree{}",
    "\u2022": r"\textbullet{}",
    "\u00a9": r"\textcopyright{}",
    "\u00ae": r"\textregistered{}",
    "\u2122": r"\texttrademark{}",
    "\u00b1": r"\textpm{}",
    "\u00d7": r"\texttimes{}",
    "\u00f7": r"\textdiv{}",
}


def latex_escape(text: str | None) -> str:
    """
    Escape special LaTeX characters in text.

    Handles:
    - LaTeX special chars: & % $ # _ { } < > |
    - Backslash, tilde, caret (multi-step to avoid double-escaping)
    - Unicode smart quotes, dashes, ellipsis, symbols
    - Straight quotes to LaTeX quotes
    """
    if text is None:
        return ""
    result = str(text)
    result = result.replace("\\", _BACKSLASH_PLACEHOLDER)
    result = result.replace("~", _TILDE_PLACEHOLDER)
    result = result.replace("^", _CARET_PLACEHOLDER)
    for char, replacement in LATEX_SPECIAL_CHARS.items():
        result = result.replace(char, replacement)
    for char, replacement in UNICODE_REPLACEMENTS.items():
        result = result.replace(char, replacement)
    result = result.replace('"', "''")
    result = result.replace(_BACKSLASH_PLACEHOLDER, r"\textbackslash{}")
    result = result.replace(_TILDE_PLACEHOLDER, r"\textasciitilde{}")
    result = result.replace(_CARET_PLACEHOLDER, r"\textasciicircum{}")
    return result


def hex_to_rgb(hex_color: str) -> str:
    """Convert hex color (#RRGGBB) to RGB triplet string (R, G, B)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "0, 0, 0"
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    except ValueError:
        return "0, 0, 0"


@dataclass
class TemplateConfig:
    """Configuration passed to LaTeX templates."""

    font_family: str = "sans"
    margin_top: str = "0.6in"
    margin_bottom: str = "0.5in"
    margin_left: str = "0.65in"
    margin_right: str = "0.65in"
    primary_color: str = "45, 85, 145"
    secondary_color: str = "60, 60, 60"
    accent_color: str = "100, 100, 100"

    @classmethod
    def from_settings(cls, settings: Settings) -> TemplateConfig:
        """Create template config from application settings."""
        margin = f"{settings.margin_inches}in"
        return cls(
            font_family="sans",
            margin_top=margin,
            margin_bottom=margin,
            margin_left=margin,
            margin_right=margin,
            primary_color=hex_to_rgb(settings.primary_color),
            secondary_color=hex_to_rgb(settings.secondary_color),
            accent_color="100, 100, 100",
        )


class LaTeXGenerator:
    """Converts ResumeDocument to LaTeX source using Jinja2 templating."""

    def __init__(
        self,
        settings: Settings | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        self._settings = settings
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._env = self._create_jinja_env()

    def _create_jinja_env(self) -> Environment:
        """Create Jinja2 environment with LaTeX-friendly delimiters."""
        env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(enabled_extensions=()),
            block_start_string="((*",
            block_end_string="*))",
            variable_start_string="(((",
            variable_end_string=")))",
            comment_start_string="((#",
            comment_end_string="#))",
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["latex_escape"] = latex_escape
        return env

    def generate(
        self,
        resume: ResumeDocument,
        template: ResumeTemplate | None = None,
        config: TemplateConfig | None = None,
    ) -> str:
        """
        Generate LaTeX source from a ResumeDocument.

        Args:
            resume: The resume document to render
            template: Template to use (defaults to settings.default_template or MODERN)
            config: Template configuration (defaults to settings-derived config)

        Returns:
            Generated LaTeX source code
        """
        if template is None:
            template = self._settings.default_template if self._settings else ResumeTemplate.MODERN
        tpl = self._env.get_template(f"{template.value}.tex")
        if config is None:
            config = (
                TemplateConfig.from_settings(self._settings)
                if self._settings
                else TemplateConfig()
            )
        context = self._build_context(resume, config)
        return tpl.render(**context)

    def generate_to_file(
        self,
        resume: ResumeDocument,
        output_path: Path,
        template: ResumeTemplate | None = None,
        config: TemplateConfig | None = None,
    ) -> Path:
        """
        Generate LaTeX source and write to file.

        Args:
            resume: The resume document to render
            output_path: Where to write the .tex file
            template: Template to use
            config: Template configuration

        Returns:
            Path to the generated file
        """
        latex_source = self.generate(resume, template, config)
        output_path = output_path.with_suffix(".tex")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(latex_source, encoding="utf-8")
        return output_path

    def _build_context(
        self,
        resume: ResumeDocument,
        config: TemplateConfig,
    ) -> dict[str, object]:
        """Build the template context from resume document."""
        return {
            "config": config,
            "contact": resume.contact,
            "professional_summary": resume.professional_summary,
            "headline": resume.headline,
            "experiences": resume.experiences,
            "education": resume.education,
            "skills": resume.skills,
            "certifications": resume.certifications,
            "projects": resume.projects,
            "additional_sections": [s for s in resume.additional_sections if s.visible],
        }

    def list_templates(self) -> list[str]:
        """List available template names."""
        return [t.value for t in ResumeTemplate]

    def validate_template(self, template: ResumeTemplate) -> bool:
        """Check if a template file exists."""
        template_path = self._templates_dir / f"{template.value}.tex"
        return template_path.exists()

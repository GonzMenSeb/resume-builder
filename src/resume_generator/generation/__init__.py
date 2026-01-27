"""LaTeX generation module for resume rendering."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

from .generator import LaTeXGenerator, TemplateConfig, latex_escape  # noqa: E402

__all__ = ["TEMPLATES_DIR", "LaTeXGenerator", "TemplateConfig", "latex_escape"]

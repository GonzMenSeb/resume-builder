"""LaTeX generation module for resume rendering."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

from .compiler import CompilationError, CompilationResult, PDFCompiler  # noqa: E402
from .generator import LaTeXGenerator, TemplateConfig, latex_escape  # noqa: E402

__all__ = [
    "TEMPLATES_DIR",
    "CompilationError",
    "CompilationResult",
    "LaTeXGenerator",
    "PDFCompiler",
    "TemplateConfig",
    "latex_escape",
]

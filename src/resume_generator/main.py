"""CLI entry point for the resume generator."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import HttpUrl
from rich.console import Console

from resume_generator import __version__
from resume_generator.claude_client import ClaudeCLI
from resume_generator.config import (
    CONFIG_FILE_NAME,
    ClaudeModel,
    ColorPalette,
    ResumeLanguage,
    ResumeTemplate,
    Settings,
    find_config_file,
    get_default_config_template,
    get_settings,
)
from resume_generator.models.job import JobDescription
from resume_generator.pipeline import PipelineError, ResumePipeline
from resume_generator.ui.progress import PipelineConfig, PipelineUI
from resume_generator.utils.web import FetchError, fetch_and_extract_text

app = typer.Typer(
    name="resume-gen",
    help="S+ tier resume generator powered by Claude AI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold bright_cyan]resume-gen[/] version [bold]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """S+ tier resume generator powered by Claude AI."""


@app.command()
def generate(
    inputs: Annotated[
        list[Path] | None,
        typer.Argument(
            help="Input files or directories (PDF, DOCX, TXT, MD). If omitted, uses input_dir from config.",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path for generated resume (PDF/LaTeX)",
        ),
    ] = None,
    job_description: Annotated[
        str | None,
        typer.Option(
            "--job",
            "-j",
            help="Job description text for tailoring",
        ),
    ] = None,
    job_file: Annotated[
        Path | None,
        typer.Option(
            "--job-file",
            "-J",
            help="Path to file containing job description",
            exists=True,
            readable=True,
        ),
    ] = None,
    job_url: Annotated[
        str | None,
        typer.Option(
            "--job-url",
            "-u",
            help="URL to job posting (will fetch and extract text)",
        ),
    ] = None,
    template: Annotated[
        ResumeTemplate,
        typer.Option(
            "--template",
            "-t",
            help="Resume template to use",
            case_sensitive=False,
        ),
    ] = ResumeTemplate.MODERN,
    claude_model: Annotated[
        ClaudeModel | None,
        typer.Option(
            "--claude-model",
            "-m",
            help="Claude model to use for AI operations",
            case_sensitive=False,
        ),
    ] = None,
    no_compile: Annotated[
        bool,
        typer.Option(
            "--no-compile",
            help="Skip PDF compilation (output LaTeX only)",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-V",
            help="Enable verbose output",
        ),
    ] = False,
    language: Annotated[
        ResumeLanguage | None,
        typer.Option(
            "--language",
            "-l",
            help="Output language for the resume (e.g., en, es, fr, de)",
            case_sensitive=False,
        ),
    ] = None,
    max_pages: Annotated[
        int | None,
        typer.Option(
            "--max-pages",
            "-p",
            help="Maximum pages for the final resume (1-3)",
            min=1,
            max=3,
        ),
    ] = None,
    max_bullet_words: Annotated[
        int | None,
        typer.Option(
            "--max-bullet-words",
            "-w",
            help="Maximum words per bullet point (10-50)",
            min=10,
            max=50,
        ),
    ] = None,
    color_palette: Annotated[
        ColorPalette | None,
        typer.Option(
            "--colors",
            "-c",
            help="Color palette (classic, burgundy, navy, forest, slate, charcoal)",
            case_sensitive=False,
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            "-L",
            help="Log level for pipeline file logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Path to YAML config file",
            exists=True,
            readable=True,
        ),
    ] = None,
) -> None:
    """Generate an S+ tier resume from input data.

    Provide one or more input files (PDF, DOCX, TXT, MD) or directories containing
    your resume data. If no inputs are provided, uses input_dir from config.
    Optionally specify a job description to tailor the resume for that
    specific position.

    [bold]Examples:[/]

        [dim]# Generate using input_dir from config (simplest)[/]
        resume-gen generate

        [dim]# Generate from a single PDF[/]
        resume-gen generate ./my_resume.pdf

        [dim]# Generate with job tailoring from URL[/]
        resume-gen generate ./data/ --job-url https://example.com/job-posting

        [dim]# Generate with specific template and output path[/]
        resume-gen generate ./data/ -t ats -o ./output/resume.pdf

        [dim]# Use a specific Claude model[/]
        resume-gen generate ./data/ --claude-model opus

        [dim]# Verbose output for debugging[/]
        resume-gen generate ./data/ -V --job "Senior Python Developer..."

        [dim]# Generate resume in Spanish[/]
        resume-gen generate ./data/ --language es

        [dim]# Use a custom config file[/]
        resume-gen generate ./data/ --config my-config.yaml
    """
    if not ClaudeCLI.available():
        console.print(
            "[bold red]Claude CLI not found.[/] "
            "Please install it first: https://github.com/anthropics/claude-code"
        )
        raise typer.Exit(1)

    used_config_file = config_file or find_config_file()
    if verbose and used_config_file:
        console.print(f"[dim]Using config: {used_config_file}[/]")

    try:
        settings = _build_settings(
            config_file=config_file,
            no_compile=no_compile,
            verbose=verbose,
            claude_model=claude_model,
            language=language,
            max_pages=max_pages,
            max_bullet_words=max_bullet_words,
            color_palette=color_palette,
            log_level=log_level,
        )
    except Exception as e:
        console.print(f"[bold red]Configuration error:[/] {e}")
        raise typer.Exit(1) from e

    resolved_inputs = _resolve_inputs(inputs, settings, verbose)
    job = _parse_job_description(
        job_description, job_file, job_url, verbose, settings.target_job_dir
    )

    pipeline_config = PipelineConfig.from_settings(settings)
    ui = PipelineUI(verbose=verbose, config=pipeline_config)
    pipeline = ResumePipeline(settings=settings, ui=ui)

    try:
        result = pipeline.run(
            sources=resolved_inputs,
            output_path=output,
            job=job,
            template=template,
        )
        if not result.success:
            console.print("[bold red]Resume generation failed.[/]")
            for error in result.errors:
                console.print(f"  [red]• {error}[/]")
            raise typer.Exit(1)

        log_dir = settings.output_dir / "logs"
        if log_dir.exists():
            console.print(f"[dim]Logs written to: {log_dir}[/]")

    except PipelineError as e:
        console.print(f"\n[bold red]Pipeline error:[/] {e}")
        if e.stage:
            console.print(f"  [dim]Failed at stage: {e.stage.value}[/]")
        raise typer.Exit(1) from e
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/]")
        raise typer.Exit(130) from None
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


def _resolve_inputs(
    inputs: list[Path] | None,
    settings: Settings,
    verbose: bool,
) -> list[Path]:
    """Resolve input sources from CLI arguments or config file."""
    if inputs:
        return inputs

    if settings.input_dir:
        input_path = settings.input_dir
        if not input_path.exists():
            console.print(f"[bold red]Input directory not found:[/] {input_path}")
            raise typer.Exit(1)
        if verbose:
            console.print(f"[dim]Using input_dir from config: {input_path}[/]")
        return [input_path]

    console.print(
        "[bold red]No input sources provided.[/]\n"
        "Either provide input files/directories as arguments, or set [bold]input_dir[/] in your config file."
    )
    raise typer.Exit(1)


def _build_settings(
    *,
    config_file: Path | None,
    no_compile: bool,
    verbose: bool,
    claude_model: ClaudeModel | None,
    language: ResumeLanguage | None,
    max_pages: int | None,
    max_bullet_words: int | None,
    color_palette: ColorPalette | None,
    log_level: str | None = None,
) -> Settings:
    """Build settings from config file with CLI overrides."""
    settings = get_settings(config_path=config_file)
    updates: dict[str, bool | int | str | ClaudeModel | ResumeLanguage | ColorPalette] = {}
    if no_compile:
        updates["compile_pdf"] = False
    if verbose:
        updates["verbose"] = True
    if claude_model is not None:
        updates["claude_model"] = claude_model
    if language is not None:
        updates["output_language"] = language
    if max_pages is not None:
        updates["max_pages"] = max_pages
    if max_bullet_words is not None:
        updates["max_bullet_words"] = max_bullet_words
    if color_palette is not None and color_palette != settings.color_palette:
        updates["color_palette"] = color_palette
    if log_level is not None:
        updates["log_level"] = log_level
    if updates:
        settings = settings.model_copy(update=updates)
    return settings


def _parse_job_description(
    job_text: str | None,
    job_file: Path | None,
    job_url: str | None,
    verbose: bool,
    target_job_dir: Path | None = None,
) -> JobDescription | None:
    """Parse job description from text, file, URL, or target_job_dir config."""
    if job_file:
        text = job_file.read_text(encoding="utf-8")
        return JobDescription(title="Target Position", raw_text=text)
    if job_url:
        text = _fetch_job_url(job_url, verbose)
        return JobDescription(
            title="Target Position",
            raw_text=text,
            posting_url=HttpUrl(job_url),
        )
    if job_text:
        return JobDescription(title="Target Position", raw_text=job_text)
    if target_job_dir and target_job_dir.exists():
        job_files = list(target_job_dir.glob("*.txt")) + list(target_job_dir.glob("*.md"))
        if job_files:
            latest_job_file = max(job_files, key=lambda f: f.stat().st_mtime)
            if verbose:
                console.print(f"[dim]Using job description from target_job_dir: {latest_job_file}[/]")
            text = latest_job_file.read_text(encoding="utf-8")
            return JobDescription(title="Target Position", raw_text=text)
    return None


def _fetch_job_url(url: str, verbose: bool) -> str:
    """Fetch job posting content from URL."""
    if verbose:
        console.print(f"[dim]Fetching job posting from: {url}[/]")

    try:
        text = fetch_and_extract_text(url)
    except FetchError as e:
        raise typer.BadParameter(f"Failed to fetch URL: {e}") from e

    if verbose:
        console.print(f"[dim]Extracted {len(text)} characters from job posting[/]")
    return text


@app.command()
def init(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path for config file",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing config file",
        ),
    ] = False,
) -> None:
    """Initialize a configuration file with default settings.

    Creates a resume-gen.yaml file in the current directory that you can
    edit to customize pipeline behavior.

    [bold]Examples:[/]

        [dim]# Create config in current directory[/]
        resume-gen init

        [dim]# Create config at specific path[/]
        resume-gen init -o ~/.resume-gen.yaml

        [dim]# Overwrite existing config[/]
        resume-gen init --force
    """
    config_path = output or (Path.cwd() / CONFIG_FILE_NAME)

    if config_path.exists() and not force:
        console.print(
            f"[yellow]Config file already exists:[/] {config_path}\n"
            "Use [bold]--force[/] to overwrite."
        )
        raise typer.Exit(1)

    config_content = get_default_config_template()
    config_path.write_text(config_content, encoding="utf-8")
    console.print(f"[green]Created config file:[/] {config_path}")


@app.command()
def config(
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            "-s",
            help="Show current effective configuration",
        ),
    ] = True,
) -> None:
    """Show current configuration and config file location.

    [bold]Examples:[/]

        [dim]# Show current config[/]
        resume-gen config
    """
    config_file = find_config_file()

    if config_file:
        console.print(f"[bold]Config file:[/] {config_file}")
    else:
        console.print("[dim]No config file found. Run 'resume-gen init' to create one.[/]")

    if show:
        console.print("\n[bold]Effective settings:[/]")
        settings = get_settings()
        console.print(f"  max_pages: {settings.max_pages}")
        console.print(f"  max_bullet_words: {settings.max_bullet_words}")
        console.print(f"  color_palette: {settings.color_palette.value}")
        console.print(f"  claude_model: {settings.claude_model.value}")
        console.print(f"  output_language: {settings.output_language.value}")
        console.print(f"  compile_pdf: {settings.compile_pdf}")
        console.print(f"  min_bullets_per_job: {settings.min_bullets_per_job}")
        console.print(f"  max_bullets_per_job: {settings.max_bullets_per_job}")
        console.print(f"  log_level: {settings.log_level}")


if __name__ == "__main__":
    app()

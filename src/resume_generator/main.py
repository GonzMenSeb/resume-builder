"""CLI entry point for the resume generator."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from resume_generator import __version__
from resume_generator.config import ResumeTemplate, Settings, get_settings
from resume_generator.models.job import JobDescription
from resume_generator.pipeline import PipelineError, ResumePipeline
from resume_generator.ui.progress import PipelineUI

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
        list[Path],
        typer.Argument(
            help="Input files or directories (PDF, TXT, MD)",
            exists=True,
            readable=True,
        ),
    ],
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
    template: Annotated[
        ResumeTemplate,
        typer.Option(
            "--template",
            "-t",
            help="Resume template to use",
            case_sensitive=False,
        ),
    ] = ResumeTemplate.MODERN,
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
) -> None:
    """Generate an S+ tier resume from input data.

    Provide one or more input files (PDF, TXT, MD) or directories containing
    your resume data. Optionally specify a job description to tailor the
    resume for that specific position.

    [bold]Examples:[/]

        [dim]# Generate from a single PDF[/]
        resume-gen generate ./my_resume.pdf

        [dim]# Generate with job tailoring[/]
        resume-gen generate ./data/ --job "Senior Python Developer at..."

        [dim]# Generate with specific template and output path[/]
        resume-gen generate ./data/ -t ats -o ./output/resume.pdf
    """
    try:
        settings = _build_settings(no_compile, verbose)
    except Exception as e:
        console.print(f"[bold red]Configuration error:[/] {e}")
        raise typer.Exit(1) from e

    job = _parse_job_description(job_description, job_file)

    ui = PipelineUI(verbose=verbose)
    pipeline = ResumePipeline(settings=settings, ui=ui)

    try:
        result = pipeline.run(
            sources=inputs,
            output_path=output,
            job=job,
            template=template,
        )
        if not result.success:
            console.print("[bold red]Resume generation failed.[/]")
            for error in result.errors:
                console.print(f"  [red]• {error}[/]")
            raise typer.Exit(1)

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


def _build_settings(no_compile: bool, verbose: bool) -> Settings:
    """Build settings with CLI overrides."""
    settings = get_settings()
    if no_compile:
        settings = Settings(
            anthropic_api_key=settings.anthropic_api_key,
            compile_pdf=False,
            verbose=verbose,
        )
    elif verbose:
        settings = Settings(
            anthropic_api_key=settings.anthropic_api_key,
            verbose=True,
        )
    return settings


def _parse_job_description(
    job_text: str | None,
    job_file: Path | None,
) -> JobDescription | None:
    """Parse job description from text or file."""
    if job_file:
        text = job_file.read_text(encoding="utf-8")
        return JobDescription(title="Target Position", raw_text=text)
    if job_text:
        return JobDescription(title="Target Position", raw_text=job_text)
    return None


if __name__ == "__main__":
    app()

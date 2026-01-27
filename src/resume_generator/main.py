"""CLI entry point for the resume generator."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import httpx
import typer
from pydantic import HttpUrl
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

        [dim]# Generate with job tailoring from URL[/]
        resume-gen generate ./data/ --job-url https://example.com/job-posting

        [dim]# Generate with specific template and output path[/]
        resume-gen generate ./data/ -t ats -o ./output/resume.pdf

        [dim]# Verbose output for debugging[/]
        resume-gen generate ./data/ -V --job "Senior Python Developer..."
    """
    try:
        settings = _build_settings(no_compile, verbose)
    except Exception as e:
        console.print(f"[bold red]Configuration error:[/] {e}")
        raise typer.Exit(1) from e

    job = _parse_job_description(job_description, job_file, job_url, verbose)

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
    job_url: str | None,
    verbose: bool,
) -> JobDescription | None:
    """Parse job description from text, file, or URL."""
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
    return None


def _fetch_job_url(url: str, verbose: bool) -> str:
    """Fetch job posting content from URL."""
    if verbose:
        console.print(f"[dim]Fetching job posting from: {url}[/]")

    try:
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ResumeGen/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = client.get(url, headers=headers)
            response.raise_for_status()
            content = response.text
    except httpx.HTTPStatusError as e:
        raise typer.BadParameter(
            f"Failed to fetch URL (HTTP {e.response.status_code}): {url}"
        ) from e
    except httpx.RequestError as e:
        raise typer.BadParameter(f"Failed to fetch URL: {e}") from e

    text = _extract_text_from_html(content)
    if verbose:
        console.print(f"[dim]Extracted {len(text)} characters from job posting[/]")
    return text


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


if __name__ == "__main__":
    app()

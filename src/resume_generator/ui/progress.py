"""Pipeline UI with colorful Rich console output for progress tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import time
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.style import Style
from rich.table import Table
from rich.text import Text


class PipelineStage(str, Enum):
    """Pipeline processing stages."""

    LOADING = "loading"
    EXTRACTING = "extracting"
    OPTIMIZING = "optimizing"
    TAILORING = "tailoring"
    GENERATING = "generating"
    COMPILING = "compiling"


@dataclass
class StageInfo:
    """Information about a pipeline stage."""

    name: str
    icon: str
    description: str
    color: str


STAGE_CONFIG: dict[PipelineStage, StageInfo] = {
    PipelineStage.LOADING: StageInfo(
        name="Loading Data",
        icon="📄",
        description="Reading and parsing input files",
        color="cyan",
    ),
    PipelineStage.EXTRACTING: StageInfo(
        name="Extracting Profile",
        icon="🔍",
        description="Extracting structured data with AI",
        color="yellow",
    ),
    PipelineStage.OPTIMIZING: StageInfo(
        name="Optimizing Content",
        icon="✨",
        description="Enhancing bullets with X-Y-Z formula",
        color="magenta",
    ),
    PipelineStage.TAILORING: StageInfo(
        name="Tailoring Resume",
        icon="🎯",
        description="Customizing for target job",
        color="blue",
    ),
    PipelineStage.GENERATING: StageInfo(
        name="Generating LaTeX",
        icon="📝",
        description="Creating LaTeX source",
        color="green",
    ),
    PipelineStage.COMPILING: StageInfo(
        name="Compiling PDF",
        icon="🖨️",
        description="Running pdflatex",
        color="bright_green",
    ),
}


@dataclass
class PipelineStats:
    """Statistics collected during pipeline execution."""

    files_loaded: int = 0
    total_characters: int = 0
    experiences_extracted: int = 0
    skills_extracted: int = 0
    bullets_optimized: int = 0
    keywords_matched: int = 0
    keyword_match_rate: float = 0.0
    optimization_score: float = 0.0
    output_path: Path | None = None
    errors: list[str] = field(default_factory=list)


class PipelineUI:
    """Rich-based UI for pipeline progress visualization."""

    def __init__(self, verbose: bool = False) -> None:
        self.console = Console()
        self.verbose = verbose
        self._live: Live | None = None
        self._progress: Progress | None = None
        self._stage_task_id: TaskID | None = None
        self._overall_task_id: TaskID | None = None
        self._current_stage: PipelineStage | None = None
        self._stage_times: dict[PipelineStage, float] = {}
        self._start_time: float = 0.0
        self._stats = PipelineStats()
        self._completed_stages: set[PipelineStage] = set()

    @property
    def stats(self) -> PipelineStats:
        """Access pipeline statistics."""
        return self._stats

    def _create_progress(self) -> Progress:
        """Create progress bar with custom columns."""
        return Progress(
            SpinnerColumn(style="bold cyan"),
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=40, style="cyan", complete_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            expand=False,
        )

    def _build_header(self) -> Panel:
        """Build the header panel."""
        title = Text()
        title.append("✨ ", style="bright_yellow")
        title.append("Resume Generator", style="bold bright_white")
        title.append(" ✨", style="bright_yellow")
        return Panel(
            title,
            style="bold cyan",
            border_style="bright_blue",
            padding=(0, 2),
        )

    def _build_stages_panel(self) -> Panel:
        """Build the stages status panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Status", width=3)
        table.add_column("Stage", width=25)
        table.add_column("Time", justify="right", width=10)

        for stage in PipelineStage:
            info = STAGE_CONFIG[stage]

            if stage in self._completed_stages:
                status = Text("✓", style="bold green")
                elapsed = self._stage_times.get(stage, 0.0)
                time_str = f"{elapsed:.1f}s"
                name_style = "dim"
            elif stage == self._current_stage:
                status = Text("●", style=f"bold {info.color} blink")
                time_str = "..."
                name_style = f"bold {info.color}"
            else:
                status = Text("○", style="dim")
                time_str = ""
                name_style = "dim"

            table.add_row(
                status,
                Text(f"{info.icon} {info.name}", style=name_style),
                Text(time_str, style="dim"),
            )

        return Panel(
            table,
            title="[bold]Pipeline Stages",
            border_style="blue",
            padding=(0, 1),
        )

    def _build_stats_panel(self) -> Panel:
        """Build the statistics panel."""
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Label", style="dim")
        stats_table.add_column("Value", style="bold")

        if self._stats.files_loaded > 0:
            stats_table.add_row("Files Loaded", str(self._stats.files_loaded))
        if self._stats.total_characters > 0:
            chars = f"{self._stats.total_characters:,}"
            stats_table.add_row("Characters", chars)
        if self._stats.experiences_extracted > 0:
            stats_table.add_row("Experiences", str(self._stats.experiences_extracted))
        if self._stats.skills_extracted > 0:
            stats_table.add_row("Skills", str(self._stats.skills_extracted))
        if self._stats.bullets_optimized > 0:
            stats_table.add_row("Bullets", str(self._stats.bullets_optimized))
        if self._stats.keyword_match_rate > 0:
            rate = f"{self._stats.keyword_match_rate:.0%}"
            color = "green" if self._stats.keyword_match_rate >= 0.7 else "yellow"
            stats_table.add_row("Keyword Match", Text(rate, style=color))
        if self._stats.optimization_score > 0:
            score = f"{self._stats.optimization_score:.0%}"
            color = "green" if self._stats.optimization_score >= 0.8 else "yellow"
            stats_table.add_row("Optimization", Text(score, style=color))

        return Panel(
            stats_table,
            title="[bold]Statistics",
            border_style="magenta",
            padding=(0, 1),
        )

    def _build_display(self) -> Group:
        """Build the complete display."""
        elements: list[Any] = [self._build_header()]

        if self._progress:
            elements.append(self._progress)

        elements.append(self._build_stages_panel())

        if any(
            [
                self._stats.files_loaded,
                self._stats.experiences_extracted,
                self._stats.bullets_optimized,
            ]
        ):
            elements.append(self._build_stats_panel())

        return Group(*elements)

    def start_pipeline(self, stages: list[PipelineStage] | None = None) -> None:
        """Start the pipeline UI with live display."""
        self._start_time = time()
        self._stats = PipelineStats()
        self._completed_stages = set()
        self._stage_times = {}

        self._progress = self._create_progress()
        total_stages = len(stages) if stages else len(PipelineStage)
        self._overall_task_id = self._progress.add_task(
            "[bold cyan]Overall Progress",
            total=total_stages,
        )

        self._live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=10,
            transient=False,
        )
        self._live.start()

    def update_stage(
        self,
        stage: PipelineStage,
        *,
        completed: bool = False,
        message: str | None = None,
    ) -> None:
        """Update current stage status."""
        if completed:
            if self._current_stage:
                elapsed = time() - self._stage_times.get(self._current_stage, time())
                self._stage_times[self._current_stage] = elapsed
                self._completed_stages.add(self._current_stage)

            if self._progress and self._overall_task_id is not None:
                self._progress.advance(self._overall_task_id)

            self._current_stage = None
        else:
            self._current_stage = stage
            self._stage_times[stage] = time()

            if self._progress:
                info = STAGE_CONFIG[stage]
                desc = message or info.description
                if self._stage_task_id is not None:
                    self._progress.update(
                        self._stage_task_id,
                        description=f"[{info.color}]{info.icon} {desc}",
                    )
                else:
                    self._stage_task_id = self._progress.add_task(
                        f"[{info.color}]{info.icon} {desc}",
                        total=None,
                    )

        if self._live:
            self._live.update(self._build_display())

    def show_progress(self, current: int, total: int, message: str = "") -> None:
        """Update progress within current stage."""
        if self._progress and self._stage_task_id is not None:
            self._progress.update(
                self._stage_task_id,
                completed=current,
                total=total,
                description=message if message else None,
            )
        if self._live:
            self._live.update(self._build_display())

    def log(self, message: str, style: str = "") -> None:
        """Log a message (only shown in verbose mode)."""
        if self.verbose:
            self.console.print(f"  {message}", style=style or "dim")

    def show_success(self, output_path: Path | None = None) -> None:
        """Display success message with summary."""
        if self._live:
            self._live.stop()
            self._live = None

        self._stats.output_path = output_path
        total_time = time() - self._start_time

        self.console.print()
        success_panel = self._build_success_panel(total_time, output_path)
        self.console.print(success_panel)

    def _build_success_panel(self, total_time: float, output_path: Path | None) -> Panel:
        """Build the success summary panel."""
        content = Table(show_header=False, box=None, padding=(0, 2))
        content.add_column("Label", style="dim")
        content.add_column("Value", style="bold")

        content.add_row("Status", Text("✓ Complete", style="bold green"))
        content.add_row("Total Time", f"{total_time:.1f}s")

        if self._stats.experiences_extracted > 0:
            content.add_row("Experiences", str(self._stats.experiences_extracted))
        if self._stats.bullets_optimized > 0:
            content.add_row("Bullets Optimized", str(self._stats.bullets_optimized))
        if self._stats.keyword_match_rate > 0:
            rate = f"{self._stats.keyword_match_rate:.0%}"
            content.add_row("Keyword Match Rate", Text(rate, style="green"))
        if self._stats.optimization_score > 0:
            score = f"{self._stats.optimization_score:.0%}"
            content.add_row("Optimization Score", Text(score, style="green"))
        if output_path:
            content.add_row("Output", Text(str(output_path), style="cyan underline"))

        return Panel(
            content,
            title="[bold green]✨ Resume Generated Successfully!",
            border_style="green",
            style=Style(bgcolor="grey7"),
            padding=(1, 2),
        )

    def show_error(self, error: str | Exception, stage: PipelineStage | None = None) -> None:
        """Display error message."""
        if self._live:
            self._live.stop()
            self._live = None

        error_msg = str(error)
        self._stats.errors.append(error_msg)

        stage_info = ""
        if stage:
            info = STAGE_CONFIG[stage]
            stage_info = f"{info.icon} {info.name}: "

        self.console.print()
        error_panel = Panel(
            Text(f"{stage_info}{error_msg}", style="bold red"),
            title="[bold red]❌ Pipeline Error",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print(error_panel)

    def stop(self) -> None:
        """Stop the live display."""
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self) -> PipelineUI:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

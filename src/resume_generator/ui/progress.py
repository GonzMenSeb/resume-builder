"""Pipeline UI with clean Rich console output for progress tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from resume_generator.config import Settings


class PipelineStage(str, Enum):
    """Pipeline processing stages."""

    LOADING = "loading"
    EXTRACTING = "extracting"
    OPTIMIZING = "optimizing"
    TAILORING = "tailoring"
    GENERATING = "generating"
    COMPILING = "compiling"
    REFINING = "refining"


@dataclass
class StageInfo:
    """Information about a pipeline stage."""

    name: str
    description: str


STAGE_CONFIG: dict[PipelineStage, StageInfo] = {
    PipelineStage.LOADING: StageInfo(
        name="Loading Data",
        description="Reading and parsing input files",
    ),
    PipelineStage.EXTRACTING: StageInfo(
        name="Extracting Profile",
        description="Extracting structured data with AI",
    ),
    PipelineStage.OPTIMIZING: StageInfo(
        name="Optimizing Content",
        description="Enhancing bullets with X-Y-Z formula",
    ),
    PipelineStage.TAILORING: StageInfo(
        name="Tailoring Resume",
        description="Customizing for target job",
    ),
    PipelineStage.GENERATING: StageInfo(
        name="Generating LaTeX",
        description="Creating LaTeX source",
    ),
    PipelineStage.COMPILING: StageInfo(
        name="Compiling PDF",
        description="Running pdflatex",
    ),
    PipelineStage.REFINING: StageInfo(
        name="Refining Resume",
        description="Adversarial critique and polish",
    ),
}

COLOR_PRIMARY = "cyan"
COLOR_SUCCESS = "green"
COLOR_DIM = "dim"
COLOR_MUTED = "bright_black"

STAGE_LABELS = [
    "Loading Data",
    "Extracting Profile",
    "Optimizing Content",
    "Generating LaTeX",
    "Compiling PDF",
    "Refining Resume",
]


class StageElapsedColumn(ProgressColumn):
    """Shows elapsed time for active/finished tasks."""

    def render(self, task: Task) -> Text:
        if task.finished:
            elapsed = task.elapsed if task.elapsed is not None else 0.0
            return Text(f"{elapsed:.1f}s", style=COLOR_DIM)
        elif task.started:
            elapsed = task.elapsed if task.elapsed is not None else 0.0
            return Text(f"{elapsed:.1f}s", style=COLOR_PRIMARY)
        return Text("", style=COLOR_MUTED)


@dataclass
class PipelineConfig:
    """Configuration values displayed during pipeline execution."""

    max_pages: int = 1
    max_bullet_words: int = 25
    max_bullets_per_job: int = 5
    claude_model: str = "sonnet"
    output_language: str = "en"
    color_palette: str = "classic"

    @classmethod
    def from_settings(cls, settings: Settings) -> PipelineConfig:
        return cls(
            max_pages=settings.max_pages,
            max_bullet_words=settings.max_bullet_words,
            max_bullets_per_job=settings.max_bullets_per_job,
            claude_model=settings.claude_model.value,
            output_language=settings.output_language.value,
            color_palette=settings.color_palette.value,
        )


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
    refinement_iterations: int = 0
    final_grade: str | None = None
    target_grade: str | None = None
    target_unattainable: bool = False
    max_achievable_grade: str | None = None


PIPELINE_STAGE_TO_DISPLAY_INDEX: dict[PipelineStage, int] = {
    PipelineStage.LOADING: 0,
    PipelineStage.EXTRACTING: 1,
    PipelineStage.OPTIMIZING: 2,
    PipelineStage.GENERATING: 3,
    PipelineStage.COMPILING: 4,
    PipelineStage.REFINING: 5,
}


class SummaryPanel:
    """Renders a summary panel with stats and output path."""

    def __init__(self, stats: PipelineStats, total_time: float = 0.0) -> None:
        self.stats = stats
        self.total_time = total_time

    def _build_mini_bar(self, value: float, width: int = 12) -> str:
        filled = int(value * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    def _get_score_grade(self, value: float) -> str:
        if value >= 0.95:
            return "S+"
        elif value >= 0.90:
            return "S"
        elif value >= 0.85:
            return "A+"
        elif value >= 0.80:
            return "A"
        elif value >= 0.70:
            return "B"
        elif value >= 0.60:
            return "C"
        return "D"

    def _build_stats_table(self) -> Table:
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Label", width=22)
        table.add_column("Value", justify="right")

        if self.stats.files_loaded > 0:
            table.add_row("Files Processed", str(self.stats.files_loaded))
        if self.stats.total_characters > 0:
            table.add_row("Characters Parsed", f"{self.stats.total_characters:,}")
        if self.stats.experiences_extracted > 0:
            table.add_row("Work Experiences", str(self.stats.experiences_extracted))
        if self.stats.skills_extracted > 0:
            table.add_row("Skills Identified", str(self.stats.skills_extracted))
        if self.stats.bullets_optimized > 0:
            table.add_row("Bullets Optimized", str(self.stats.bullets_optimized))
        if self.stats.refinement_iterations > 0:
            table.add_row("Refinement Iterations", str(self.stats.refinement_iterations))
        if self.stats.final_grade:
            grade_text = self.stats.final_grade
            if self.stats.target_grade:
                grade_text = f"{self.stats.final_grade} (target: {self.stats.target_grade})"
            if self.stats.target_unattainable and self.stats.max_achievable_grade:
                grade_text = f"{self.stats.final_grade} (max: {self.stats.max_achievable_grade})"
            table.add_row("Final Grade", grade_text)
        if self.stats.target_unattainable:
            table.add_row("Status", "Target unattainable")

        return table

    def _build_score_row(self, label: str, value: float) -> Text:
        bar = self._build_mini_bar(value)
        grade = self._get_score_grade(value)
        text = Text()
        text.append(f"{label:<18} ", style="default")
        text.append(bar, style=COLOR_PRIMARY)
        text.append(f" {value:.0%}  {grade}", style="bold" if value >= 0.80 else "default")
        return text

    def render(self) -> Panel:
        sections: list[RenderableType] = []

        header = Text()
        header.append("Pipeline Complete", style=f"bold {COLOR_SUCCESS}")
        header.append(f"  {self.total_time:.1f}s", style=COLOR_DIM)
        sections.append(header)
        sections.append(Text())

        stats_table = self._build_stats_table()
        if stats_table.row_count > 0:
            sections.append(stats_table)
            sections.append(Text())

        if self.stats.final_grade is None and self.stats.optimization_score > 0:
            sections.append(self._build_score_row("Quality Score", self.stats.optimization_score))
        if self.stats.final_grade is None and self.stats.keyword_match_rate > 0:
            sections.append(self._build_score_row("Keyword Match", self.stats.keyword_match_rate))

        if self.stats.output_path:
            sections.append(Text())
            output_text = Text()
            output_text.append("Output: ", style=COLOR_DIM)
            output_text.append(str(self.stats.output_path), style=f"bold {COLOR_PRIMARY}")
            sections.append(output_text)

        return Panel(
            Group(*sections),
            title=f"[{COLOR_PRIMARY}]Summary",
            border_style=COLOR_MUTED,
            padding=(1, 2),
        )


class PipelineUI:
    """Rich-based UI for pipeline progress visualization."""

    def __init__(
        self,
        verbose: bool = False,
        config: PipelineConfig | None = None,
    ) -> None:
        self.console = Console()
        self.verbose = verbose
        self._config = config
        self._live: Live | None = None
        self._overall_progress: Progress | None = None
        self._stages_progress: Progress | None = None
        self._overall_task_id: TaskID | None = None
        self._stage_task_ids: list[TaskID] = []
        self._current_stage: PipelineStage | None = None
        self._stage_times: dict[PipelineStage, float] = {}
        self._stage_start_times: dict[PipelineStage, float] = {}
        self._start_time: float = 0.0
        self._stats = PipelineStats()
        self._completed_stages: set[PipelineStage] = set()

    @property
    def stats(self) -> PipelineStats:
        """Access pipeline statistics."""
        return self._stats

    def _create_overall_progress(self) -> Progress:
        """Create the overall pipeline progress bar."""
        return Progress(
            SpinnerColumn("dots", style=COLOR_PRIMARY),
            TextColumn("[bold]{task.description}"),
            BarColumn(
                bar_width=40,
                style=COLOR_MUTED,
                complete_style=COLOR_PRIMARY,
                finished_style=COLOR_SUCCESS,
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            expand=False,
        )

    def _create_stages_progress(self) -> Progress:
        """Create progress tracker for individual stages with animated spinner."""
        return Progress(
            SpinnerColumn("dots", style=COLOR_PRIMARY, finished_text=f"[{COLOR_SUCCESS}]✓[/]"),
            TextColumn("{task.description:<22}"),
            StageElapsedColumn(),
            console=self.console,
            expand=False,
        )

    def _build_header(self) -> RenderableType:
        """Build header."""
        text = Text()
        text.append("Resume Generator", style="bold")
        return text

    def _build_config_panel(self) -> Panel:
        """Build the configuration panel."""
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Label")
        table.add_column("Value", justify="right")

        if self._config:
            table.add_row("Pages", Text(str(self._config.max_pages), style=COLOR_PRIMARY))
            table.add_row("Bullet words", Text(str(self._config.max_bullet_words), style=COLOR_DIM))
            table.add_row("Bullets/job", Text(str(self._config.max_bullets_per_job), style=COLOR_DIM))
            table.add_row("Model", Text(self._config.claude_model, style=COLOR_DIM))
            table.add_row("Palette", Text(self._config.color_palette, style=COLOR_DIM))
            table.add_row("Language", Text(self._config.output_language, style=COLOR_DIM))

        return Panel(
            table,
            title=f"[{COLOR_PRIMARY}]Config",
            border_style=COLOR_MUTED,
            padding=(0, 1),
        )

    def _build_stats_panel(self) -> Panel | None:
        """Build the statistics panel."""
        has_stats = any(
            [
                self._stats.files_loaded,
                self._stats.experiences_extracted,
                self._stats.bullets_optimized,
                self._stats.optimization_score > 0,
            ]
        )
        if not has_stats:
            return None

        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Label")
        table.add_column("Value", justify="right")

        if self._stats.files_loaded > 0:
            table.add_row("Files", str(self._stats.files_loaded))
        if self._stats.total_characters > 0:
            table.add_row("Characters", f"{self._stats.total_characters:,}")
        if self._stats.experiences_extracted > 0:
            table.add_row("Experiences", str(self._stats.experiences_extracted))
        if self._stats.skills_extracted > 0:
            table.add_row("Skills", str(self._stats.skills_extracted))
        if self._stats.bullets_optimized > 0:
            table.add_row("Bullets Optimized", str(self._stats.bullets_optimized))
        if self._stats.optimization_score > 0:
            score = f"{self._stats.optimization_score:.0%}"
            table.add_row("Quality Score", Text(score, style="bold"))

        return Panel(
            table,
            title=f"[{COLOR_PRIMARY}]Stats",
            border_style=COLOR_MUTED,
            padding=(0, 1),
        )

    def _build_display(self) -> Group:
        """Build the complete display."""
        elements: list[RenderableType] = []

        elements.append(
            Panel(
                self._build_header(),
                border_style=COLOR_MUTED,
                padding=(0, 2),
            )
        )

        if self._overall_progress:
            elements.append(Padding(self._overall_progress, (1, 1)))

        if self._stages_progress:
            stages_panel = Panel(
                self._stages_progress,
                title=f"[{COLOR_PRIMARY}]Pipeline Stages",
                border_style=COLOR_MUTED,
                padding=(0, 1),
            )
            config_panel = self._build_config_panel()

            columns = Table.grid(expand=True)
            columns.add_column(ratio=1)
            columns.add_column(ratio=2)
            columns.add_row(config_panel, stages_panel)
            elements.append(columns)

        stats_panel = self._build_stats_panel()
        if stats_panel:
            elements.append(stats_panel)

        return Group(*elements)

    def start_pipeline(self, stages: list[PipelineStage] | None = None) -> None:
        """Start the pipeline UI with live display."""
        self._start_time = time()
        self._stats = PipelineStats()
        self._completed_stages = set()
        self._stage_times = {}
        self._stage_start_times = {}
        self._current_stage = None
        self._stage_task_ids = []

        self._overall_progress = self._create_overall_progress()
        self._stages_progress = self._create_stages_progress()

        total_stages = len(stages) if stages else len(PipelineStage)
        self._overall_task_id = self._overall_progress.add_task(
            "Building resume",
            total=total_stages,
        )

        for label in STAGE_LABELS:
            task_id = self._stages_progress.add_task(
                label,
                total=1,
                visible=True,
                start=False,
            )
            self._stage_task_ids.append(task_id)

        self.console.print()
        self._live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=12,
            transient=False,
            vertical_overflow="visible",
        )
        self._live.start()

    def update_stage(
        self,
        stage: PipelineStage,
        *,
        completed: bool = False,
        message: str | None = None,  # noqa: ARG002
    ) -> None:
        """Update current stage status."""
        _ = message
        display_idx = PIPELINE_STAGE_TO_DISPLAY_INDEX.get(stage)

        if completed:
            if self._current_stage:
                start = self._stage_start_times.get(self._current_stage, time())
                elapsed = time() - start
                self._stage_times[self._current_stage] = elapsed
                self._completed_stages.add(self._current_stage)

                curr_idx = PIPELINE_STAGE_TO_DISPLAY_INDEX.get(self._current_stage)
                if curr_idx is not None and self._stages_progress:
                    task_id = self._stage_task_ids[curr_idx]
                    self._stages_progress.stop_task(task_id)
                    self._stages_progress.update(task_id, completed=1)

            if self._overall_progress and self._overall_task_id is not None:
                self._overall_progress.advance(self._overall_task_id)

            self._current_stage = None
        else:
            self._current_stage = stage
            self._stage_start_times[stage] = time()

            if display_idx is not None and self._stages_progress:
                self._stages_progress.start_task(self._stage_task_ids[display_idx])

        if self._live:
            self._live.update(self._build_display())

    def show_progress(
        self,
        current: int,  # noqa: ARG002
        total: int,  # noqa: ARG002
        message: str = "",  # noqa: ARG002
    ) -> None:
        """Update progress within current stage."""
        del current, total, message
        if self._live:
            self._live.update(self._build_display())

    def log(self, message: str, style: str = "") -> None:
        """Log a message (only shown in verbose mode)."""
        if self.verbose:
            self.console.print(f"  {message}", style=style or COLOR_DIM)

    def show_success(self, output_path: Path | None = None) -> None:
        """Display success message with summary."""
        if self._live:
            self._live.stop()
            self._live = None

        self._stats.output_path = output_path

        self.console.print()
        self.console.print(Rule(style=COLOR_MUTED))
        self.show_summary()
        self.console.print()

    def show_summary(self) -> None:
        """Display the summary panel."""
        total_time = time() - self._start_time if self._start_time > 0 else 0.0
        summary = SummaryPanel(self._stats, total_time)
        self.console.print(summary.render())

    def show_error(self, error: str | Exception, stage: PipelineStage | None = None) -> None:
        """Display error message with context."""
        if self._live:
            self._live.stop()
            self._live = None

        error_msg = str(error)
        self._stats.errors.append(error_msg)

        content = Table(show_header=False, box=None, padding=(0, 1))
        content.add_column("Label", style=COLOR_DIM)
        content.add_column("Value")

        if stage:
            info = STAGE_CONFIG[stage]
            content.add_row("Stage:", info.name)

        content.add_row("Error:", Text(error_msg, style="bold red"))

        if self._start_time > 0:
            elapsed = time() - self._start_time
            content.add_row("Elapsed:", f"{elapsed:.1f}s")

        self.console.print()
        self.console.print(Rule(style="red"))
        self.console.print(
            Panel(
                content,
                title="[red]Error",
                border_style="red",
                padding=(1, 2),
            )
        )
        self.console.print()

    def stop(self) -> None:
        """Stop the live display."""
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self) -> PipelineUI:
        return self

    def __exit__(
        self,
        exc_type: Any,  # noqa: ARG002
        exc_val: Any,  # noqa: ARG002
        exc_tb: Any,  # noqa: ARG002
    ) -> None:
        del exc_type, exc_val, exc_tb
        self.stop()

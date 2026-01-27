"""Pipeline UI with colorful Rich console output for progress tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import time
from typing import Any

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
        color="bright_cyan",
    ),
    PipelineStage.EXTRACTING: StageInfo(
        name="Extracting Profile",
        icon="🔍",
        description="Extracting structured data with AI",
        color="bright_yellow",
    ),
    PipelineStage.OPTIMIZING: StageInfo(
        name="Optimizing Content",
        icon="✨",
        description="Enhancing bullets with X-Y-Z formula",
        color="bright_magenta",
    ),
    PipelineStage.TAILORING: StageInfo(
        name="Tailoring Resume",
        icon="🎯",
        description="Customizing for target job",
        color="bright_blue",
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

STAGE_SPINNERS: dict[PipelineStage, str] = {
    PipelineStage.LOADING: "dots",
    PipelineStage.EXTRACTING: "dots12",
    PipelineStage.OPTIMIZING: "arc",
    PipelineStage.TAILORING: "bouncingBall",
    PipelineStage.GENERATING: "dots8Bit",
    PipelineStage.COMPILING: "aesthetic",
}


class StageProgressColumn(ProgressColumn):
    """Custom column showing stage-specific styled progress."""

    def render(self, task: Task) -> RenderableType:
        if task.total is None:
            return Text("")
        completed = int(task.completed)
        total = int(task.total)
        return Text(f"[{completed}/{total}]", style="dim cyan")


@dataclass
class StageDisplayConfig:
    """Configuration for stage display elements."""

    icon: str
    label: str
    color: str


STAGE_DISPLAY_CONFIG: list[StageDisplayConfig] = [
    StageDisplayConfig("📄", "Loading Data", "bright_cyan"),
    StageDisplayConfig("🔍", "Extracting Profile", "bright_yellow"),
    StageDisplayConfig("✨", "Optimizing Content", "bright_magenta"),
    StageDisplayConfig("📝", "Generating LaTeX", "green"),
    StageDisplayConfig("🖨️", "Compiling PDF", "bright_green"),
]


class StageProgressBar:
    """Visual progress bar for a single stage."""

    WIDTH = 12

    def __init__(self, config: StageDisplayConfig) -> None:
        self.config = config
        self.active = False
        self.completed = False
        self.progress = 0.0
        self.start_time: float | None = None
        self.end_time: float | None = None

    def render(self, spinner_frame: str = "⠋") -> RenderableType:
        icon = self.config.icon
        label = self.config.label
        color = self.config.color

        if self.completed:
            status_icon = "✓"
            status_style = "bold bright_green"
            bar = "█" * self.WIDTH
            bar_style = f"dim {color}"
            elapsed = (self.end_time or time()) - (self.start_time or time())
            time_str = f" {elapsed:.1f}s"
        elif self.active:
            status_icon = spinner_frame
            status_style = f"bold {color}"
            filled = int(self.progress * self.WIDTH)
            bar = "█" * filled + "▓" + "░" * (self.WIDTH - filled - 1)
            bar_style = color
            elapsed = time() - (self.start_time or time())
            time_str = f" {elapsed:.1f}s"
        else:
            status_icon = "○"
            status_style = "dim grey50"
            bar = "░" * self.WIDTH
            bar_style = "dim grey30"
            time_str = ""

        text = Text()
        text.append(f"{status_icon} ", style=status_style)
        text.append(f"{icon} ", style=color if (self.active or self.completed) else "dim")
        text.append(
            f"{label:<18} ",
            style=f"bold {color}"
            if self.active
            else (f"dim {color}" if self.completed else "dim grey50"),
        )
        text.append(bar, style=bar_style)
        text.append(time_str, style="dim cyan")

        return text


class StageProgressDisplay:
    """Live stage-by-stage progress visualization component."""

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self) -> None:
        self._stages = [StageProgressBar(cfg) for cfg in STAGE_DISPLAY_CONFIG]
        self._current_idx = -1
        self._spinner_idx = 0
        self._last_tick = time()

    def start_stage(self, index: int) -> None:
        if 0 <= index < len(self._stages):
            self._current_idx = index
            self._stages[index].active = True
            self._stages[index].start_time = time()
            self._stages[index].progress = 0.0

    def complete_stage(self, index: int) -> None:
        if 0 <= index < len(self._stages):
            self._stages[index].active = False
            self._stages[index].completed = True
            self._stages[index].progress = 1.0
            self._stages[index].end_time = time()

    def update_progress(self, index: int, progress: float) -> None:
        if 0 <= index < len(self._stages):
            self._stages[index].progress = min(1.0, max(0.0, progress))

    def _tick_spinner(self) -> str:
        now = time()
        if now - self._last_tick > 0.08:
            self._spinner_idx = (self._spinner_idx + 1) % len(self.SPINNER_FRAMES)
            self._last_tick = now
        return self.SPINNER_FRAMES[self._spinner_idx]

    def render(self) -> RenderableType:
        spinner = self._tick_spinner()
        elements = [stage.render(spinner) for stage in self._stages]
        return Group(*elements)

    def render_panel(self) -> Panel:
        return Panel(
            self.render(),
            title="[bold bright_white]⚡ Pipeline Stages",
            border_style="bright_blue",
            padding=(0, 1),
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


PIPELINE_STAGE_TO_DISPLAY_INDEX: dict[PipelineStage, int] = {
    PipelineStage.LOADING: 0,
    PipelineStage.EXTRACTING: 1,
    PipelineStage.OPTIMIZING: 2,
    PipelineStage.GENERATING: 3,
    PipelineStage.COMPILING: 4,
}


class SummaryPanel:
    """Renders a comprehensive summary panel with extraction stats, optimization score, and output path."""

    def __init__(self, stats: PipelineStats, total_time: float = 0.0) -> None:
        self.stats = stats
        self.total_time = total_time

    def _build_mini_bar(self, value: float, width: int = 15) -> str:
        filled = int(value * width)
        partial = int((value * width - filled) * 2)
        empty = width - filled - (1 if partial else 0)
        partial_char = "▓" if partial else ""
        return "█" * filled + partial_char + "░" * empty

    def _get_score_color(self, value: float) -> str:
        if value >= 0.85:
            return "bold bright_green"
        elif value >= 0.70:
            return "bright_green"
        elif value >= 0.50:
            return "yellow"
        return "bright_red"

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

    def _build_extraction_section(self) -> Table:
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Icon", width=3, justify="center")
        table.add_column("Label", width=20)
        table.add_column("Value", justify="right")

        if self.stats.files_loaded > 0:
            table.add_row(
                "📁",
                "Files Processed",
                Text(str(self.stats.files_loaded), style="bold bright_cyan"),
            )
        if self.stats.total_characters > 0:
            chars = f"{self.stats.total_characters:,}"
            table.add_row("📊", "Characters Parsed", Text(chars, style="cyan"))
        if self.stats.experiences_extracted > 0:
            table.add_row(
                "💼",
                "Work Experiences",
                Text(str(self.stats.experiences_extracted), style="bold bright_yellow"),
            )
        if self.stats.skills_extracted > 0:
            table.add_row(
                "🎯",
                "Skills Identified",
                Text(str(self.stats.skills_extracted), style="bold bright_magenta"),
            )
        if self.stats.bullets_optimized > 0:
            table.add_row(
                "✨",
                "Bullets Optimized",
                Text(str(self.stats.bullets_optimized), style="bold green"),
            )

        return table

    def _build_optimization_section(self) -> Table:
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Metric", width=18)
        table.add_column("Bar", width=17, justify="center")
        table.add_column("Score", width=8, justify="right")
        table.add_column("Grade", width=4, justify="center")

        if self.stats.keyword_match_rate > 0:
            rate = self.stats.keyword_match_rate
            bar = self._build_mini_bar(rate)
            color = self._get_score_color(rate)
            grade = self._get_score_grade(rate)
            table.add_row(
                Text("🔑 Keyword Match", style="bright_white"),
                Text(bar, style=color),
                Text(f"{rate:.0%}", style=color),
                Text(grade, style=color),
            )

        if self.stats.optimization_score > 0:
            score = self.stats.optimization_score
            bar = self._build_mini_bar(score)
            color = self._get_score_color(score)
            grade = self._get_score_grade(score)
            table.add_row(
                Text("⚡ Quality Score", style="bright_white"),
                Text(bar, style=color),
                Text(f"{score:.0%}", style=color),
                Text(grade, style=color),
            )

        return table

    def _build_output_section(self) -> Text:
        text = Text()
        if self.stats.output_path:
            text.append("📄 ", style="bright_green")
            text.append("Output: ", style="bright_white")
            text.append(str(self.stats.output_path), style="bold bright_cyan underline")
        return text

    def render(self) -> Panel:
        sections: list[RenderableType] = []

        header = Text()
        header.append("✅ ", style="bold bright_green")
        header.append("Pipeline Complete", style="bold bright_green")
        header.append(" • ", style="dim")
        header.append(f"{self.total_time:.1f}s", style="bright_cyan")
        sections.append(header)
        sections.append(Text())

        extraction = self._build_extraction_section()
        if extraction.row_count > 0:
            sections.append(Text("─── Extraction Stats ───", style="dim bright_cyan"))
            sections.append(extraction)
            sections.append(Text())

        optimization = self._build_optimization_section()
        if optimization.row_count > 0:
            sections.append(Text("─── Optimization Score ───", style="dim bright_magenta"))
            sections.append(optimization)
            sections.append(Text())

        if self.stats.output_path:
            sections.append(Text("─── Output ───", style="dim bright_green"))
            sections.append(self._build_output_section())

        content = Group(*sections)

        return Panel(
            content,
            title="[bold bright_white]📊 Resume Generation Summary",
            border_style="bright_blue",
            style=Style(bgcolor="grey7"),
            padding=(1, 2),
        )


class PipelineUI:
    """Rich-based UI for pipeline progress visualization."""

    GRADIENT_COLORS = ["#ff6b6b", "#feca57", "#48dbfb", "#1dd1a1", "#5f27cd", "#00d2d3"]

    def __init__(self, verbose: bool = False) -> None:
        self.console = Console()
        self.verbose = verbose
        self._live: Live | None = None
        self._progress: Progress | None = None
        self._stage_progress: Progress | None = None
        self._stage_task_id: TaskID | None = None
        self._overall_task_id: TaskID | None = None
        self._current_stage: PipelineStage | None = None
        self._stage_times: dict[PipelineStage, float] = {}
        self._stage_start_times: dict[PipelineStage, float] = {}
        self._start_time: float = 0.0
        self._stats = PipelineStats()
        self._completed_stages: set[PipelineStage] = set()
        self._status_message: str = ""
        self._stage_display = StageProgressDisplay()

    @property
    def stats(self) -> PipelineStats:
        """Access pipeline statistics."""
        return self._stats

    def _create_overall_progress(self) -> Progress:
        """Create the overall pipeline progress bar."""
        return Progress(
            SpinnerColumn("dots", style="bold bright_cyan"),
            TextColumn("[bold bright_white]{task.description}"),
            BarColumn(
                bar_width=50,
                style="grey37",
                complete_style="bright_green",
                finished_style="bold bright_green",
                pulse_style="bright_cyan",
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            expand=False,
        )

    def _create_stage_progress(self, stage: PipelineStage) -> Progress:
        """Create stage-specific spinner progress."""
        info = STAGE_CONFIG[stage]
        spinner = STAGE_SPINNERS.get(stage, "dots")
        return Progress(
            SpinnerColumn(spinner, style=f"bold {info.color}"),
            TextColumn(f"[bold {info.color}]{{task.description}}"),
            BarColumn(
                bar_width=30,
                style="grey30",
                complete_style=info.color,
                finished_style=f"bold {info.color}",
            ),
            StageProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            expand=False,
        )

    def _build_header(self) -> Panel:
        """Build the header panel with gradient title."""
        title = Text()
        title.append("╭─", style="bright_cyan")
        title.append("─", style="bright_blue")
        title.append("─", style="bright_magenta")
        title.append("╮ ", style="bright_green")
        title.append("S+ ", style="bold bright_yellow")
        title.append("Resume Generator", style="bold bright_white")
        title.append(" ╭", style="bright_green")
        title.append("─", style="bright_magenta")
        title.append("─", style="bright_blue")
        title.append("─╮", style="bright_cyan")
        return Panel(
            title,
            style="bold cyan",
            border_style="bright_blue",
            padding=(0, 2),
        )

    def _build_current_action(self) -> Panel | None:
        """Build panel showing current action with spinner."""
        if not self._current_stage or not self._stage_progress:
            return None

        info = STAGE_CONFIG[self._current_stage]
        return Panel(
            self._stage_progress,
            title=f"[bold {info.color}]{info.icon} {info.name}",
            subtitle=f"[dim]{self._status_message}[/]" if self._status_message else None,
            border_style=info.color,
            padding=(0, 1),
        )

    def _build_stages_panel(self) -> Panel:
        """Build the stages status panel with visual progress indicators."""
        table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
        table.add_column("Status", width=3, justify="center")
        table.add_column("Stage", width=22)
        table.add_column("Description", style="dim", ratio=1)
        table.add_column("Time", justify="right", width=8)

        for stage in PipelineStage:
            info = STAGE_CONFIG[stage]

            if stage in self._completed_stages:
                status = Text("✓", style="bold bright_green")
                elapsed = self._stage_times.get(stage, 0.0)
                time_str = f"{elapsed:.1f}s"
                name_style = "dim green"
                desc_style = "dim"
            elif stage == self._current_stage:
                status = Text("▸", style=f"bold {info.color}")
                start = self._stage_start_times.get(stage, time())
                elapsed = time() - start
                time_str = f"{elapsed:.1f}s"
                name_style = f"bold {info.color}"
                desc_style = info.color
            else:
                status = Text("○", style="dim grey50")
                time_str = "—"
                name_style = "dim grey50"
                desc_style = "dim grey37"

            table.add_row(
                status,
                Text(f"{info.icon} {info.name}", style=name_style),
                Text(info.description, style=desc_style),
                Text(time_str, style="dim" if stage != self._current_stage else info.color),
            )

        return Panel(
            table,
            title="[bold bright_white]Pipeline Progress",
            border_style="bright_blue",
            padding=(0, 1),
        )

    def _build_stats_panel(self) -> Panel:
        """Build the statistics panel with visual indicators."""
        stats_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        stats_table.add_column("Icon", width=3, justify="center")
        stats_table.add_column("Label", style="bright_white")
        stats_table.add_column("Value", style="bold", justify="right")

        if self._stats.files_loaded > 0:
            stats_table.add_row(
                "📁", "Files Loaded", Text(str(self._stats.files_loaded), style="cyan")
            )
        if self._stats.total_characters > 0:
            chars = f"{self._stats.total_characters:,}"
            stats_table.add_row("📊", "Characters", Text(chars, style="cyan"))
        if self._stats.experiences_extracted > 0:
            stats_table.add_row(
                "💼", "Experiences", Text(str(self._stats.experiences_extracted), style="yellow")
            )
        if self._stats.skills_extracted > 0:
            stats_table.add_row(
                "🎯", "Skills", Text(str(self._stats.skills_extracted), style="magenta")
            )
        if self._stats.bullets_optimized > 0:
            stats_table.add_row(
                "✨", "Bullets Optimized", Text(str(self._stats.bullets_optimized), style="green")
            )
        if self._stats.keyword_match_rate > 0:
            rate = f"{self._stats.keyword_match_rate:.0%}"
            bar = self._build_mini_bar(self._stats.keyword_match_rate)
            color = "bright_green" if self._stats.keyword_match_rate >= 0.7 else "yellow"
            stats_table.add_row("🔑", "Keyword Match", Text(f"{bar} {rate}", style=color))
        if self._stats.optimization_score > 0:
            score = f"{self._stats.optimization_score:.0%}"
            bar = self._build_mini_bar(self._stats.optimization_score)
            color = "bright_green" if self._stats.optimization_score >= 0.8 else "yellow"
            stats_table.add_row("⚡", "Optimization", Text(f"{bar} {score}", style=color))

        return Panel(
            stats_table,
            title="[bold bright_magenta]📈 Statistics",
            border_style="bright_magenta",
            padding=(0, 1),
        )

    def _build_mini_bar(self, value: float, width: int = 10) -> str:
        """Build a mini progress bar string."""
        filled = int(value * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    def _build_display(self) -> Group:
        """Build the complete display."""
        elements: list[RenderableType] = [self._build_header()]

        if self._progress:
            elements.append(Padding(self._progress, (0, 1)))

        current_action = self._build_current_action()
        if current_action:
            elements.append(current_action)

        elements.append(self._stage_display.render_panel())

        has_stats = any(
            [
                self._stats.files_loaded,
                self._stats.experiences_extracted,
                self._stats.bullets_optimized,
                self._stats.keyword_match_rate > 0,
                self._stats.optimization_score > 0,
            ]
        )
        if has_stats:
            elements.append(self._build_stats_panel())

        return Group(*elements)

    def start_pipeline(self, stages: list[PipelineStage] | None = None) -> None:
        """Start the pipeline UI with live display.

        Args:
            stages: List of stages to run. If None, uses all stages.
        """
        self._start_time = time()
        self._stats = PipelineStats()
        self._completed_stages = set()
        self._stage_times = {}
        self._stage_start_times = {}
        self._current_stage = None
        self._status_message = ""
        self._stage_progress = None
        self._stage_task_id = None
        self._stage_display = StageProgressDisplay()

        self._progress = self._create_overall_progress()
        total_stages = len(stages) if stages else len(PipelineStage)
        self._overall_task_id = self._progress.add_task(
            "🚀 Building your S+ resume",
            total=total_stages,
        )

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
        message: str | None = None,
    ) -> None:
        """Update current stage status.

        Args:
            stage: The pipeline stage to update.
            completed: Whether this stage is completed.
            message: Optional status message to display.
        """
        display_idx = PIPELINE_STAGE_TO_DISPLAY_INDEX.get(stage)

        if completed:
            if self._current_stage:
                start = self._stage_start_times.get(self._current_stage, time())
                self._stage_times[self._current_stage] = time() - start
                self._completed_stages.add(self._current_stage)

            if self._progress and self._overall_task_id is not None:
                self._progress.advance(self._overall_task_id)

            if display_idx is not None:
                self._stage_display.complete_stage(display_idx)

            self._current_stage = None
            self._stage_progress = None
            self._stage_task_id = None
            self._status_message = ""
        else:
            self._current_stage = stage
            self._stage_start_times[stage] = time()
            self._status_message = message or ""

            if display_idx is not None:
                self._stage_display.start_stage(display_idx)

            self._stage_progress = self._create_stage_progress(stage)
            info = STAGE_CONFIG[stage]
            desc = message or info.description
            self._stage_task_id = self._stage_progress.add_task(
                desc,
                total=None,
            )

        if self._live:
            self._live.update(self._build_display())

    def show_progress(self, current: int, total: int, message: str = "") -> None:
        """Update progress within current stage.

        Args:
            current: Current progress value.
            total: Total expected value.
            message: Optional message to display alongside progress.
        """
        if self._stage_progress and self._stage_task_id is not None:
            self._stage_progress.update(
                self._stage_task_id,
                completed=current,
                total=total,
                description=message if message else None,
            )

        if self._current_stage is not None:
            display_idx = PIPELINE_STAGE_TO_DISPLAY_INDEX.get(self._current_stage)
            if display_idx is not None and total > 0:
                self._stage_display.update_progress(display_idx, current / total)

        if message:
            self._status_message = message
        if self._live:
            self._live.update(self._build_display())

    def log(self, message: str, style: str = "") -> None:
        """Log a message (only shown in verbose mode)."""
        if self.verbose:
            self.console.print(f"  {message}", style=style or "dim")

    def show_success(self, output_path: Path | None = None) -> None:
        """Display success message with summary.

        Args:
            output_path: Path to the generated output file.
        """
        if self._live:
            self._live.stop()
            self._live = None

        self._stats.output_path = output_path

        self.console.print()
        self.console.print(Rule(style="bright_green"))
        self.show_summary()
        self.console.print()

    def show_summary(self) -> None:
        """Display the summary panel with extraction stats, optimization score, and output path."""
        total_time = time() - self._start_time if self._start_time > 0 else 0.0
        summary = SummaryPanel(self._stats, total_time)
        self.console.print(summary.render())

    def _build_success_panel(self, total_time: float, output_path: Path | None) -> Panel:
        """Build the success summary panel with celebration styling."""
        content = Table(show_header=False, box=None, padding=(0, 2), expand=True)
        content.add_column("Icon", width=3, justify="center")
        content.add_column("Label", style="bright_white")
        content.add_column("Value", style="bold", justify="right")

        content.add_row("✅", "Status", Text("Complete", style="bold bright_green"))
        content.add_row("⏱️ ", "Total Time", Text(f"{total_time:.1f}s", style="bright_cyan"))

        if self._stats.files_loaded > 0:
            content.add_row(
                "📁", "Files Processed", Text(str(self._stats.files_loaded), style="cyan")
            )
        if self._stats.experiences_extracted > 0:
            content.add_row(
                "💼", "Experiences", Text(str(self._stats.experiences_extracted), style="yellow")
            )
        if self._stats.skills_extracted > 0:
            content.add_row(
                "🎯", "Skills Extracted", Text(str(self._stats.skills_extracted), style="magenta")
            )
        if self._stats.bullets_optimized > 0:
            content.add_row(
                "✨",
                "Bullets Optimized",
                Text(str(self._stats.bullets_optimized), style="bright_green"),
            )
        if self._stats.keyword_match_rate > 0:
            rate_pct = f"{self._stats.keyword_match_rate:.0%}"
            bar = self._build_mini_bar(self._stats.keyword_match_rate)
            content.add_row("🔑", "Keyword Match", Text(f"{bar} {rate_pct}", style="bright_green"))
        if self._stats.optimization_score > 0:
            score_pct = f"{self._stats.optimization_score:.0%}"
            bar = self._build_mini_bar(self._stats.optimization_score)
            content.add_row(
                "⚡", "Optimization Score", Text(f"{bar} {score_pct}", style="bright_green")
            )
        if output_path:
            content.add_row(
                "📄", "Output File", Text(str(output_path), style="bright_cyan underline")
            )

        return Panel(
            content,
            title="[bold bright_green]🎉 S+ Resume Generated Successfully! 🎉",
            border_style="bright_green",
            style=Style(bgcolor="grey7"),
            padding=(1, 2),
        )

    def show_error(self, error: str | Exception, stage: PipelineStage | None = None) -> None:
        """Display error message with context.

        Args:
            error: Error message or exception.
            stage: Optional stage where the error occurred.
        """
        if self._live:
            self._live.stop()
            self._live = None

        error_msg = str(error)
        self._stats.errors.append(error_msg)

        error_content = Table(show_header=False, box=None, padding=(0, 1))
        error_content.add_column("Label", style="dim red")
        error_content.add_column("Value")

        if stage:
            info = STAGE_CONFIG[stage]
            error_content.add_row("Stage:", Text(f"{info.icon} {info.name}", style="bold yellow"))

        error_content.add_row("Error:", Text(error_msg, style="bold bright_red"))

        if self._start_time > 0:
            elapsed = time() - self._start_time
            error_content.add_row("Elapsed:", Text(f"{elapsed:.1f}s", style="dim"))

        completed_count = len(self._completed_stages)
        if completed_count > 0:
            stages_str = ", ".join(STAGE_CONFIG[s].name for s in self._completed_stages)
            error_content.add_row("Completed:", Text(stages_str, style="dim green"))

        self.console.print()
        self.console.print(Rule(style="red"))
        error_panel = Panel(
            error_content,
            title="[bold bright_red]❌ Pipeline Error",
            border_style="red",
            style=Style(bgcolor="grey7"),
            padding=(1, 2),
        )
        self.console.print(error_panel)
        self.console.print()

    def stop(self) -> None:
        """Stop the live display."""
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self) -> PipelineUI:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

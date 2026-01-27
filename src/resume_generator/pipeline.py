"""Main pipeline orchestrating: ingestion → extraction → optimization → generation → compilation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any

from resume_generator.claude_client import ClaudeCLI, ClaudeCLINotFoundError
from resume_generator.config import ResumeTemplate, Settings, get_settings
from resume_generator.extraction.profile import ExtractionError, ProfileExtractor
from resume_generator.generation.compiler import CompilationResult, PDFCompiler
from resume_generator.generation.generator import LaTeXGenerator, TemplateConfig
from resume_generator.ingestion.loader import DataLoader, LoadResult
from resume_generator.models.job import JobDescription
from resume_generator.models.profile import PersonProfile
from resume_generator.models.resume import ResumeDocument
from resume_generator.optimization.optimizer import OptimizationError, ResumeOptimizer
from resume_generator.optimization.tailoring import JobTailorer, TailoringError
from resume_generator.ui.progress import PipelineStage, PipelineUI

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)


class StageStatus(str, Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result from a single pipeline stage."""

    stage: PipelineStage
    status: StageStatus
    duration_seconds: float = 0.0
    error: Exception | None = None
    data: Any = None


class PipelineError(Exception):
    """Raised when pipeline execution fails."""

    def __init__(
        self,
        message: str,
        stage: PipelineStage | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.cause = cause
        self.__cause__ = cause


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""

    success: bool
    pdf_path: Path | None = None
    tex_path: Path | None = None
    resume: ResumeDocument | None = None
    profile: PersonProfile | None = None
    load_result: LoadResult | None = None
    compilation_result: CompilationResult | None = None
    keyword_match_rate: float = 0.0
    optimization_score: float = 0.0
    errors: list[str] = field(default_factory=list)
    stage_results: list[StageResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0

    @property
    def output_path(self) -> Path | None:
        return self.pdf_path or self.tex_path

    @property
    def completed_stages(self) -> list[PipelineStage]:
        return [sr.stage for sr in self.stage_results if sr.status == StageStatus.COMPLETED]

    @property
    def failed_stage(self) -> PipelineStage | None:
        for sr in self.stage_results:
            if sr.status == StageStatus.FAILED:
                return sr.stage
        return None


class ResumePipeline:
    """Orchestrates the full resume generation pipeline.

    Flow: ingestion → extraction → optimization → [tailoring] → generation → compilation
    """

    def __init__(
        self,
        settings: Settings | None = None,
        ui: PipelineUI | None = None,
        claude_cli: ClaudeCLI | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ui = ui

        self._claude_cli = claude_cli or ClaudeCLI(
            model=self._settings.claude_model.value,
            timeout=self._settings.claude_cli_timeout,
        )
        self._verify_claude_cli()

        self._loader = DataLoader()
        self._extractor = ProfileExtractor(self._settings)
        self._optimizer = ResumeOptimizer(self._settings)
        self._tailorer = JobTailorer(self._settings)
        self._generator = LaTeXGenerator(self._settings)
        self._compiler = PDFCompiler()

    def _verify_claude_cli(self) -> None:
        """Verify Claude CLI is available before running pipeline."""
        if not ClaudeCLI.available():
            raise ClaudeCLINotFoundError(
                "Claude CLI is not installed or not in PATH. "
                "Please install Claude CLI to use this application. "
                "Visit https://claude.ai/code for installation instructions."
            )
        logger.debug("Claude CLI verified: %s", ClaudeCLI.version())

    @property
    def claude_cli(self) -> ClaudeCLI:
        """Access the Claude CLI client instance."""
        return self._claude_cli

    @property
    def settings(self) -> Settings:
        """Access the pipeline settings."""
        return self._settings

    def run(
        self,
        sources: Path | str | Sequence[Path | str],
        output_path: Path | None = None,
        job: JobDescription | None = None,
        template: ResumeTemplate | None = None,
    ) -> PipelineResult:
        """
        Execute the full resume generation pipeline.

        Args:
            sources: Input sources (files, directories, or raw text).
            output_path: Where to save the output PDF/LaTeX.
            job: Optional job description for tailoring.
            template: Resume template to use.

        Returns:
            PipelineResult with paths to generated files and metadata.

        Raises:
            PipelineError: If any stage fails critically.
        """
        stages = self._determine_stages(job)
        if self._ui:
            self._ui.start_pipeline(stages)

        result = PipelineResult(success=False)

        try:
            load_result = self._run_ingestion(sources)
            result.load_result = load_result

            profile = self._run_extraction(load_result.unified_text)
            result.profile = profile

            resume = self._run_optimization(profile, job)

            if job and self._settings.enable_job_tailoring:
                resume = self._run_tailoring(resume, job)

            result.resume = resume

            tex_path = self._run_generation(resume, output_path, template)
            result.tex_path = tex_path

            if self._settings.compile_pdf:
                pdf_path, compilation = self._run_compilation(tex_path, output_path)
                result.pdf_path = pdf_path
                result.compilation_result = compilation

            result.keyword_match_rate = resume.keyword_match_rate or 0.0
            result.optimization_score = resume.optimization_score or 0.0
            result.success = True

            if self._ui:
                self._update_final_stats(result)
                self._ui.show_success(result.output_path)

        except PipelineError as e:
            result.errors.append(str(e))
            if self._ui:
                self._ui.show_error(e, e.stage)
            raise
        except Exception as e:
            result.errors.append(str(e))
            if self._ui:
                self._ui.show_error(e)
            raise PipelineError(str(e)) from e
        finally:
            if self._ui:
                self._ui.stop()

        return result

    def _determine_stages(self, job: JobDescription | None) -> list[PipelineStage]:
        stages = [
            PipelineStage.LOADING,
            PipelineStage.EXTRACTING,
            PipelineStage.OPTIMIZING,
        ]
        if job and self._settings.enable_job_tailoring:
            stages.append(PipelineStage.TAILORING)
        stages.append(PipelineStage.GENERATING)
        if self._settings.compile_pdf:
            stages.append(PipelineStage.COMPILING)
        return stages

    def _run_ingestion(self, sources: Path | str | Sequence[Path | str]) -> LoadResult:
        if self._ui:
            self._ui.update_stage(PipelineStage.LOADING, message="Reading input files")

        try:
            result = self._loader.load(sources, skip_failures=True)
        except FileNotFoundError as e:
            raise PipelineError(str(e), PipelineStage.LOADING) from e

        if not result.unified_text.strip():
            raise PipelineError(
                "No text content extracted from sources",
                PipelineStage.LOADING,
            )

        if self._ui:
            self._ui.stats.files_loaded = result.source_count
            self._ui.stats.total_characters = result.total_chars
            self._ui.update_stage(PipelineStage.LOADING, completed=True)

        logger.info(
            "Loaded %d sources (%d chars)",
            result.source_count,
            result.total_chars,
        )
        return result

    def _run_extraction(self, raw_text: str) -> PersonProfile:
        if self._ui:
            self._ui.update_stage(
                PipelineStage.EXTRACTING,
                message="Analyzing with Claude AI",
            )

        try:
            profile = self._extractor.extract(raw_text)
        except ExtractionError as e:
            raise PipelineError(str(e), PipelineStage.EXTRACTING) from e

        if self._ui:
            self._ui.stats.experiences_extracted = len(profile.experiences)
            self._ui.stats.skills_extracted = len(profile.skills)
            self._ui.update_stage(PipelineStage.EXTRACTING, completed=True)

        logger.info(
            "Extracted profile: %d experiences, %d skills",
            len(profile.experiences),
            len(profile.skills),
        )
        return profile

    def _run_optimization(
        self,
        profile: PersonProfile,
        job: JobDescription | None,
    ) -> ResumeDocument:
        if self._ui:
            self._ui.update_stage(
                PipelineStage.OPTIMIZING,
                message="Applying X-Y-Z formula",
            )

        target_keywords = list(job.get_keyword_set()) if job else None
        target_title = job.title if job else None

        try:
            resume = self._optimizer.optimize(
                profile,
                target_job_title=target_title,
                target_keywords=target_keywords,
            )
        except OptimizationError as e:
            raise PipelineError(str(e), PipelineStage.OPTIMIZING) from e

        if self._ui:
            self._ui.stats.bullets_optimized = resume.total_bullet_count
            self._ui.stats.optimization_score = resume.optimization_score or 0.0
            self._ui.update_stage(PipelineStage.OPTIMIZING, completed=True)

        logger.info(
            "Optimized resume: %d bullets, score=%.2f",
            resume.total_bullet_count,
            resume.optimization_score or 0.0,
        )
        return resume

    def _run_tailoring(
        self,
        resume: ResumeDocument,
        job: JobDescription,
    ) -> ResumeDocument:
        if self._ui:
            self._ui.update_stage(
                PipelineStage.TAILORING,
                message=f"Tailoring for {job.title}",
            )

        tailored = self._tailorer.tailor(resume, job, use_ai=True)

        if self._ui:
            self._ui.stats.keyword_match_rate = tailored.keyword_match_rate or 0.0
            self._ui.update_stage(PipelineStage.TAILORING, completed=True)

        logger.info(
            "Tailored resume: match_rate=%.0f%%",
            (tailored.keyword_match_rate or 0.0) * 100,
        )
        return tailored

    def _run_generation(
        self,
        resume: ResumeDocument,
        output_path: Path | None,
        template: ResumeTemplate | None,
    ) -> Path:
        if self._ui:
            self._ui.update_stage(PipelineStage.GENERATING, message="Building LaTeX")

        template = template or self._settings.default_template
        config = TemplateConfig.from_settings(self._settings)

        if output_path is None:
            self._settings.ensure_directories()
            output_name = self._generate_output_name(resume)
            output_path = self._settings.output_dir / output_name

        tex_path = self._generator.generate_to_file(
            resume,
            output_path.with_suffix(".tex"),
            template=template,
            config=config,
        )

        if self._ui:
            self._ui.update_stage(PipelineStage.GENERATING, completed=True)

        logger.info("Generated LaTeX: %s", tex_path)
        return tex_path

    def _run_compilation(
        self,
        tex_path: Path,
        output_path: Path | None,
    ) -> tuple[Path | None, CompilationResult]:
        if self._ui:
            self._ui.update_stage(PipelineStage.COMPILING, message="Running pdflatex")

        pdf_output = output_path.with_suffix(".pdf") if output_path else None
        result = self._compiler.compile(tex_path, output_path=pdf_output)

        if not result.success:
            error_msgs = "; ".join(str(e) for e in result.errors[:3])
            raise PipelineError(
                f"PDF compilation failed: {error_msgs}",
                PipelineStage.COMPILING,
            )

        if self._ui:
            self._ui.update_stage(PipelineStage.COMPILING, completed=True)

        logger.info("Compiled PDF: %s", result.pdf_path)
        return result.pdf_path, result

    def _generate_output_name(self, resume: ResumeDocument) -> str:
        name_parts = resume.contact.name.lower().split()
        sanitized = "_".join(name_parts[:2]) if name_parts else "resume"
        sanitized = "".join(c if c.isalnum() or c == "_" else "" for c in sanitized)
        if resume.target_job_title:
            job_part = resume.target_job_title.lower().replace(" ", "_")[:20]
            job_part = "".join(c if c.isalnum() or c == "_" else "" for c in job_part)
            return f"{sanitized}_{job_part}_resume"
        return f"{sanitized}_resume"

    def _update_final_stats(self, result: PipelineResult) -> None:
        if self._ui and result.resume:
            self._ui.stats.keyword_match_rate = result.keyword_match_rate
            self._ui.stats.optimization_score = result.optimization_score

    async def run_async(
        self,
        sources: Path | str | Sequence[Path | str],
        output_path: Path | None = None,
        job: JobDescription | None = None,
        template: ResumeTemplate | None = None,
    ) -> PipelineResult:
        """
        Execute the resume generation pipeline asynchronously.

        Runs CPU-bound operations (extraction, optimization, tailoring) in a thread pool
        to avoid blocking the event loop while maintaining the same pipeline flow.

        Args:
            sources: Input sources (files, directories, or raw text).
            output_path: Where to save the output PDF/LaTeX.
            job: Optional job description for tailoring.
            template: Resume template to use.

        Returns:
            PipelineResult with paths to generated files and metadata.

        Raises:
            PipelineError: If any stage fails critically.
        """
        pipeline_start = time()
        stages = self._determine_stages(job)
        if self._ui:
            self._ui.start_pipeline(stages)

        result = PipelineResult(success=False)
        loop = asyncio.get_event_loop()

        try:
            stage_result = await self._run_stage_async(
                PipelineStage.LOADING,
                lambda: self._run_ingestion(sources),
                loop,
            )
            result.stage_results.append(stage_result)
            load_result = stage_result.data
            result.load_result = load_result

            stage_result = await self._run_stage_async(
                PipelineStage.EXTRACTING,
                lambda: self._run_extraction(load_result.unified_text),
                loop,
            )
            result.stage_results.append(stage_result)
            profile = stage_result.data
            result.profile = profile

            stage_result = await self._run_stage_async(
                PipelineStage.OPTIMIZING,
                lambda: self._run_optimization(profile, job),
                loop,
            )
            result.stage_results.append(stage_result)
            resume = stage_result.data

            if job and self._settings.enable_job_tailoring:
                stage_result = await self._run_stage_async(
                    PipelineStage.TAILORING,
                    lambda: self._run_tailoring(resume, job),
                    loop,
                )
                result.stage_results.append(stage_result)
                resume = stage_result.data

            result.resume = resume

            stage_result = await self._run_stage_async(
                PipelineStage.GENERATING,
                lambda: self._run_generation(resume, output_path, template),
                loop,
            )
            result.stage_results.append(stage_result)
            tex_path = stage_result.data
            result.tex_path = tex_path

            if self._settings.compile_pdf:
                stage_result = await self._run_stage_async(
                    PipelineStage.COMPILING,
                    lambda: self._run_compilation(tex_path, output_path),
                    loop,
                )
                result.stage_results.append(stage_result)
                pdf_path, compilation = stage_result.data
                result.pdf_path = pdf_path
                result.compilation_result = compilation

            result.keyword_match_rate = resume.keyword_match_rate or 0.0
            result.optimization_score = resume.optimization_score or 0.0
            result.success = True
            result.total_duration_seconds = time() - pipeline_start

            if self._ui:
                self._update_final_stats(result)
                self._ui.show_success(result.output_path)

        except PipelineError as e:
            result.errors.append(str(e))
            result.total_duration_seconds = time() - pipeline_start
            failed_stage_result = StageResult(
                stage=e.stage or PipelineStage.LOADING,
                status=StageStatus.FAILED,
                error=e,
            )
            result.stage_results.append(failed_stage_result)
            if self._ui:
                self._ui.show_error(e, e.stage)
            raise
        except Exception as e:
            result.errors.append(str(e))
            result.total_duration_seconds = time() - pipeline_start
            if self._ui:
                self._ui.show_error(e)
            raise PipelineError(str(e), cause=e) from e
        finally:
            if self._ui:
                self._ui.stop()

        return result

    async def _run_stage_async(
        self,
        stage: PipelineStage,
        func: Callable[[], Any],
        loop: asyncio.AbstractEventLoop,
    ) -> StageResult:
        """Run a pipeline stage asynchronously with timing and error handling."""
        start_time = time()

        try:
            data = await loop.run_in_executor(None, func)
            duration = time() - start_time
            return StageResult(
                stage=stage,
                status=StageStatus.COMPLETED,
                duration_seconds=duration,
                data=data,
            )
        except PipelineError:
            raise
        except (ExtractionError, OptimizationError, TailoringError) as e:
            raise PipelineError(str(e), stage=stage, cause=e) from e
        except Exception as e:
            raise PipelineError(f"Stage {stage.value} failed: {e}", stage=stage, cause=e) from e

    def run_with_callbacks(
        self,
        sources: Path | str | Sequence[Path | str],
        output_path: Path | None = None,
        job: JobDescription | None = None,
        template: ResumeTemplate | None = None,
        on_stage_start: Callable[[PipelineStage], None] | None = None,
        on_stage_complete: Callable[[PipelineStage, StageResult], None] | None = None,
        on_error: Callable[[PipelineStage, Exception], None] | None = None,
    ) -> PipelineResult:
        """
        Execute pipeline with custom stage callbacks.

        Useful for integrating with custom progress tracking or logging systems.

        Args:
            sources: Input sources (files, directories, or raw text).
            output_path: Where to save the output PDF/LaTeX.
            job: Optional job description for tailoring.
            template: Resume template to use.
            on_stage_start: Called when each stage begins.
            on_stage_complete: Called when each stage completes successfully.
            on_error: Called when a stage fails.

        Returns:
            PipelineResult with paths to generated files and metadata.

        Raises:
            PipelineError: If any stage fails critically.
        """
        pipeline_start = time()
        stages = self._determine_stages(job)
        if self._ui:
            self._ui.start_pipeline(stages)

        result = PipelineResult(success=False)

        def execute_stage(
            stage: PipelineStage,
            func: Callable[[], Any],
        ) -> StageResult:
            if on_stage_start:
                on_stage_start(stage)

            start_time = time()
            try:
                data = func()
                duration = time() - start_time
                stage_result = StageResult(
                    stage=stage,
                    status=StageStatus.COMPLETED,
                    duration_seconds=duration,
                    data=data,
                )
                if on_stage_complete:
                    on_stage_complete(stage, stage_result)
                return stage_result
            except PipelineError as e:
                duration = time() - start_time
                stage_result = StageResult(
                    stage=stage,
                    status=StageStatus.FAILED,
                    duration_seconds=duration,
                    error=e,
                )
                if on_error:
                    on_error(stage, e)
                raise
            except Exception as e:
                duration = time() - start_time
                error = PipelineError(str(e), stage=stage, cause=e)
                stage_result = StageResult(
                    stage=stage,
                    status=StageStatus.FAILED,
                    duration_seconds=duration,
                    error=error,
                )
                if on_error:
                    on_error(stage, error)
                raise error from e

        try:
            sr = execute_stage(PipelineStage.LOADING, lambda: self._run_ingestion(sources))
            result.stage_results.append(sr)
            load_result = sr.data
            result.load_result = load_result

            sr = execute_stage(
                PipelineStage.EXTRACTING,
                lambda: self._run_extraction(load_result.unified_text),
            )
            result.stage_results.append(sr)
            profile = sr.data
            result.profile = profile

            sr = execute_stage(
                PipelineStage.OPTIMIZING,
                lambda: self._run_optimization(profile, job),
            )
            result.stage_results.append(sr)
            resume = sr.data

            if job and self._settings.enable_job_tailoring:
                sr = execute_stage(
                    PipelineStage.TAILORING,
                    lambda: self._run_tailoring(resume, job),
                )
                result.stage_results.append(sr)
                resume = sr.data

            result.resume = resume

            sr = execute_stage(
                PipelineStage.GENERATING,
                lambda: self._run_generation(resume, output_path, template),
            )
            result.stage_results.append(sr)
            tex_path = sr.data
            result.tex_path = tex_path

            if self._settings.compile_pdf:
                sr = execute_stage(
                    PipelineStage.COMPILING,
                    lambda: self._run_compilation(tex_path, output_path),
                )
                result.stage_results.append(sr)
                pdf_path, compilation = sr.data
                result.pdf_path = pdf_path
                result.compilation_result = compilation

            result.keyword_match_rate = resume.keyword_match_rate or 0.0
            result.optimization_score = resume.optimization_score or 0.0
            result.success = True
            result.total_duration_seconds = time() - pipeline_start

            if self._ui:
                self._update_final_stats(result)
                self._ui.show_success(result.output_path)

        except PipelineError as e:
            result.errors.append(str(e))
            result.total_duration_seconds = time() - pipeline_start
            if self._ui:
                self._ui.show_error(e, e.stage)
            raise
        except Exception as e:
            result.errors.append(str(e))
            result.total_duration_seconds = time() - pipeline_start
            if self._ui:
                self._ui.show_error(e)
            raise PipelineError(str(e), cause=e) from e
        finally:
            if self._ui:
                self._ui.stop()

        return result

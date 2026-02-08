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
from resume_generator.config import ResumeTemplate, Settings, TierGrade, get_settings
from resume_generator.extraction.profile import ExtractionError, ProfileExtractor
from resume_generator.generation.compiler import CompilationResult, PDFCompiler
from resume_generator.generation.generator import LaTeXGenerator, TemplateConfig
from resume_generator.ingestion.loader import DataLoader, LoadResult
from resume_generator.logging_config import PipelineLogging
from resume_generator.models.job import JobDescription
from resume_generator.models.profile import PersonProfile
from resume_generator.models.resume import ResumeDocument
from resume_generator.optimization.optimizer import OptimizationError, ResumeOptimizer
from resume_generator.optimization.tailoring import JobTailorer, TailoringError
from resume_generator.refinement.refiner import (
    AdversarialRefiner,
    RefinementError,
    RefinementResult,
)
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
    refinement_result: RefinementResult | None = None
    keyword_match_rate: float = 0.0
    optimization_score: float = 0.0
    final_grade: TierGrade | None = None
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

        self._logging = PipelineLogging(
            log_dir=self._settings.output_dir / "logs",
            level=self._settings.log_level,
        )

        self._loader = DataLoader()
        self._extractor = ProfileExtractor(self._settings)
        self._optimizer = ResumeOptimizer(self._settings)
        self._tailorer = JobTailorer(self._settings)
        self._generator = LaTeXGenerator(self._settings)
        self._compiler = PDFCompiler()
        self._refiner = AdversarialRefiner(self._settings)

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
        self._logging.setup()

        try:
            self._logging.enter_stage("loading")
            load_result = self._run_ingestion(sources)
            result.load_result = load_result

            self._logging.enter_stage("extraction")
            profile = self._run_extraction(load_result.unified_text)
            result.profile = profile

            self._logging.enter_stage("optimization")
            resume = self._run_optimization(profile, job)

            if job and self._settings.enable_job_tailoring:
                self._logging.enter_stage("tailoring")
                resume = self._run_tailoring(resume, job)
            else:
                if not job:
                    logger.info("Skipping tailoring: no job description provided")
                else:
                    logger.info("Skipping tailoring: disabled in settings")

            result.resume = resume

            self._logging.enter_stage("generation")
            tex_path = self._run_generation(resume, output_path, template)
            result.tex_path = tex_path

            if self._settings.compile_pdf:
                self._logging.enter_stage("compilation")
                pdf_path, compilation, resume = self._run_compilation_with_compaction(
                    resume, tex_path, output_path, template
                )
                result.pdf_path = pdf_path
                result.compilation_result = compilation
                result.resume = resume
                result.tex_path = tex_path

                target_tier = self._settings.get_target_tier_grade()
                if target_tier is not None and pdf_path is not None:
                    self._logging.enter_stage("refinement")
                    raw_text = profile.raw_text if profile else None
                    refinement_result, resume, pdf_path, tex_path = self._run_refinement(
                        resume, pdf_path, tex_path, target_tier, output_path, template, raw_text
                    )
                    result.refinement_result = refinement_result
                    result.final_grade = refinement_result.final_grade
                    result.resume = resume
                    result.pdf_path = pdf_path
                    result.tex_path = tex_path
                else:
                    if target_tier is None:
                        logger.info("Skipping refinement: no target tier grade configured")

                if not self._settings.keep_latex_source and tex_path.exists():
                    tex_path.unlink()
                    result.tex_path = None
                    logger.debug("Removed LaTeX source: %s", tex_path)

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
            self._logging.teardown()
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
        if self._settings.compile_pdf and self._settings.get_target_tier_grade() is not None:
            stages.append(PipelineStage.REFINING)
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
        pdf_output = (
            output_path.with_suffix(".pdf") if output_path else tex_path.with_suffix(".pdf")
        )
        result = self._compiler.compile(tex_path, output_path=pdf_output)

        if not result.success:
            error_msgs = "; ".join(str(e) for e in result.errors[:3])
            raise PipelineError(
                f"PDF compilation failed: {error_msgs}",
                PipelineStage.COMPILING,
            )

        return result.pdf_path, result

    def _run_compilation_with_compaction(
        self,
        resume: ResumeDocument,
        tex_path: Path,
        output_path: Path | None,
        template: ResumeTemplate | None,
    ) -> tuple[Path | None, CompilationResult, ResumeDocument]:
        if self._ui:
            self._ui.update_stage(PipelineStage.COMPILING, message="Running pdflatex")

        pdf_path, compilation = self._run_compilation(tex_path, output_path)
        max_pages = self._settings.max_pages
        min_bullets = self._settings.min_bullets_per_job
        max_compaction_rounds = 5
        current_resume = resume

        for round_num in range(max_compaction_rounds):
            if compilation.page_count <= max_pages:
                break

            logger.info(
                "PDF has %d pages, compacting (round %d, max=%d)",
                compilation.page_count,
                round_num + 1,
                max_pages,
            )

            current_resume = current_resume.compact(min_bullets_per_job=min_bullets)
            tex_path = self._run_generation(current_resume, output_path, template)
            pdf_path, compilation = self._run_compilation(tex_path, output_path)

        if self._ui:
            self._ui.update_stage(PipelineStage.COMPILING, completed=True)

        logger.info("Compiled PDF: %s (%d pages)", compilation.pdf_path, compilation.page_count)
        return pdf_path, compilation, current_resume

    def _run_refinement(
        self,
        resume: ResumeDocument,
        pdf_path: Path,
        tex_path: Path,
        target_tier: TierGrade,
        output_path: Path | None,
        template: ResumeTemplate | None,
        raw_text: str | None = None,
    ) -> tuple[RefinementResult, ResumeDocument, Path, Path]:
        """Run adversarial refinement loop until target tier is achieved.

        Args:
            resume: Current resume document.
            pdf_path: Path to current PDF.
            tex_path: Path to current LaTeX source.
            target_tier: Target tier grade to achieve.
            output_path: Base output path.
            template: Resume template to use.
            raw_text: Original raw data for truth verification and content recovery.

        Returns:
            Tuple of (refinement_result, final_resume, final_pdf_path, final_tex_path).
        """
        if self._ui:
            self._ui.update_stage(
                PipelineStage.REFINING,
                message=f"Target: {target_tier.value}",
            )

        current_resume = resume
        current_pdf = pdf_path
        current_tex = tex_path

        def regenerate_callback(polished_resume: ResumeDocument) -> tuple[Path, Path]:
            nonlocal current_tex
            current_tex = self._run_generation(polished_resume, output_path, template)
            new_pdf, _ = self._run_compilation(current_tex, output_path)
            if new_pdf is None:
                raise PipelineError("PDF regeneration failed", PipelineStage.REFINING)
            return current_tex, new_pdf

        def on_iteration(iteration: Any) -> None:
            if self._ui:
                msg = f"Iter {iteration.iteration}: {iteration.grade.value}"
                self._ui.update_stage(PipelineStage.REFINING, message=msg)
            logger.info(
                "Refinement iteration %d: grade=%s",
                iteration.iteration,
                iteration.grade.value,
            )

        try:
            refinement_result = self._refiner.refine(
                resume=current_resume,
                pdf_path=current_pdf,
                target_grade=target_tier,
                raw_text=raw_text,
                regenerate_callback=regenerate_callback,
                on_iteration=on_iteration,
            )
        except RefinementError as e:
            raise PipelineError(str(e), PipelineStage.REFINING) from e

        if refinement_result.final_resume is not None:
            current_resume = refinement_result.final_resume

        if refinement_result.iterations:
            last_iteration = refinement_result.iterations[-1]
            if last_iteration.polish_result is not None:
                current_tex = self._run_generation(current_resume, output_path, template)
                compiled_pdf, _ = self._run_compilation(current_tex, output_path)
                current_pdf = compiled_pdf if compiled_pdf is not None else pdf_path

        if self._ui:
            self._ui.update_stage(PipelineStage.REFINING, completed=True)

        logger.info(
            "Refinement complete: %s (target: %s, iterations: %d)",
            refinement_result.final_grade.value,
            target_tier.value,
            refinement_result.iteration_count,
        )

        return refinement_result, current_resume, current_pdf, current_tex

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
            if result.refinement_result:
                self._ui.stats.refinement_iterations = result.refinement_result.iteration_count
                self._ui.stats.final_grade = result.refinement_result.final_grade.value
                self._ui.stats.target_grade = result.refinement_result.target_grade.value
                self._ui.stats.target_unattainable = result.refinement_result.target_unattainable
                if result.refinement_result.max_achievable_grade:
                    self._ui.stats.max_achievable_grade = (
                        result.refinement_result.max_achievable_grade.value
                    )

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
        self._logging.setup()

        try:
            self._logging.enter_stage("loading")
            stage_result = await self._run_stage_async(
                PipelineStage.LOADING,
                lambda: self._run_ingestion(sources),
                loop,
            )
            result.stage_results.append(stage_result)
            load_result = stage_result.data
            result.load_result = load_result

            self._logging.enter_stage("extraction")
            stage_result = await self._run_stage_async(
                PipelineStage.EXTRACTING,
                lambda: self._run_extraction(load_result.unified_text),
                loop,
            )
            result.stage_results.append(stage_result)
            profile = stage_result.data
            result.profile = profile

            self._logging.enter_stage("optimization")
            stage_result = await self._run_stage_async(
                PipelineStage.OPTIMIZING,
                lambda: self._run_optimization(profile, job),
                loop,
            )
            result.stage_results.append(stage_result)
            resume = stage_result.data

            if job and self._settings.enable_job_tailoring:
                self._logging.enter_stage("tailoring")
                stage_result = await self._run_stage_async(
                    PipelineStage.TAILORING,
                    lambda: self._run_tailoring(resume, job),
                    loop,
                )
                result.stage_results.append(stage_result)
                resume = stage_result.data
            else:
                if not job:
                    logger.info("Skipping tailoring: no job description provided")
                else:
                    logger.info("Skipping tailoring: disabled in settings")

            result.resume = resume

            self._logging.enter_stage("generation")
            stage_result = await self._run_stage_async(
                PipelineStage.GENERATING,
                lambda: self._run_generation(resume, output_path, template),
                loop,
            )
            result.stage_results.append(stage_result)
            tex_path = stage_result.data
            result.tex_path = tex_path

            if self._settings.compile_pdf:
                self._logging.enter_stage("compilation")
                stage_result = await self._run_stage_async(
                    PipelineStage.COMPILING,
                    lambda: self._run_compilation(tex_path, output_path),
                    loop,
                )
                result.stage_results.append(stage_result)
                pdf_path, compilation = stage_result.data
                result.pdf_path = pdf_path
                result.compilation_result = compilation

                if not self._settings.keep_latex_source and tex_path.exists():
                    tex_path.unlink()
                    result.tex_path = None
                    logger.debug("Removed LaTeX source: %s", tex_path)

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
            self._logging.teardown()
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

        self._logging.setup()

        try:
            self._logging.enter_stage("loading")
            sr = execute_stage(PipelineStage.LOADING, lambda: self._run_ingestion(sources))
            result.stage_results.append(sr)
            load_result = sr.data
            result.load_result = load_result

            self._logging.enter_stage("extraction")
            sr = execute_stage(
                PipelineStage.EXTRACTING,
                lambda: self._run_extraction(load_result.unified_text),
            )
            result.stage_results.append(sr)
            profile = sr.data
            result.profile = profile

            self._logging.enter_stage("optimization")
            sr = execute_stage(
                PipelineStage.OPTIMIZING,
                lambda: self._run_optimization(profile, job),
            )
            result.stage_results.append(sr)
            resume = sr.data

            if job and self._settings.enable_job_tailoring:
                self._logging.enter_stage("tailoring")
                sr = execute_stage(
                    PipelineStage.TAILORING,
                    lambda: self._run_tailoring(resume, job),
                )
                result.stage_results.append(sr)
                resume = sr.data
            else:
                if not job:
                    logger.info("Skipping tailoring: no job description provided")
                else:
                    logger.info("Skipping tailoring: disabled in settings")

            result.resume = resume

            self._logging.enter_stage("generation")
            sr = execute_stage(
                PipelineStage.GENERATING,
                lambda: self._run_generation(resume, output_path, template),
            )
            result.stage_results.append(sr)
            tex_path = sr.data
            result.tex_path = tex_path

            if self._settings.compile_pdf:
                self._logging.enter_stage("compilation")
                sr = execute_stage(
                    PipelineStage.COMPILING,
                    lambda: self._run_compilation(tex_path, output_path),
                )
                result.stage_results.append(sr)
                pdf_path, compilation = sr.data
                result.pdf_path = pdf_path
                result.compilation_result = compilation

                if not self._settings.keep_latex_source and tex_path.exists():
                    tex_path.unlink()
                    result.tex_path = None
                    logger.debug("Removed LaTeX source: %s", tex_path)

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
            self._logging.teardown()
            if self._ui:
                self._ui.stop()

        return result

"""Adversarial refiner that orchestrates critique and polish iterations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from resume_generator.config import TierGrade, tier_meets_target
from resume_generator.models.resume import ResumeDocument
from resume_generator.refinement.critique import CritiqueError, CritiqueResult, ResumeCritique
from resume_generator.refinement.polisher import PolishError, PolishResult, ResumePolisher

if TYPE_CHECKING:
    from resume_generator.config import Settings

logger = logging.getLogger(__name__)


class RefinementError(Exception):
    """Raised when the refinement process fails."""


@dataclass
class RefinementIteration:
    """Record of a single refinement iteration."""

    iteration: int
    grade: TierGrade
    critique: CritiqueResult
    polish_result: PolishResult | None = None


@dataclass
class RefinementResult:
    """Result of the complete refinement process."""

    success: bool
    final_grade: TierGrade
    target_grade: TierGrade
    iterations: list[RefinementIteration] = field(default_factory=list)
    final_resume: ResumeDocument | None = None
    message: str = ""
    target_unattainable: bool = False
    max_achievable_grade: TierGrade | None = None
    unattainable_reason: str = ""

    @property
    def iteration_count(self) -> int:
        return len(self.iterations)

    @property
    def grade_improved(self) -> bool:
        if len(self.iterations) < 2:
            return False
        from resume_generator.config import TIER_GRADE_ORDER

        first = TIER_GRADE_ORDER[self.iterations[0].grade]
        last = TIER_GRADE_ORDER[self.iterations[-1].grade]
        return last > first


class AdversarialRefiner:
    """Orchestrates adversarial refinement loop between Critique and Polisher agents."""

    def __init__(
        self,
        settings: Settings | None = None,
        critique: ResumeCritique | None = None,
        polisher: ResumePolisher | None = None,
    ) -> None:
        self._settings = settings
        self._critique = critique or ResumeCritique(settings)
        self._polisher = polisher or ResumePolisher(settings)

        if settings:
            self._max_iterations = settings.max_refinement_iterations
        else:
            self._max_iterations = 5

    def refine(
        self,
        resume: ResumeDocument,
        pdf_path: Path,
        target_grade: TierGrade,
        raw_text: str | None = None,
        regenerate_callback: Callable[[ResumeDocument], tuple[Path, Path]] | None = None,
        on_iteration: Callable[[RefinementIteration], None] | None = None,
    ) -> RefinementResult:
        """Run adversarial refinement loop until target grade is achieved.

        Args:
            resume: The current ResumeDocument.
            pdf_path: Path to the current PDF.
            target_grade: The target tier grade to achieve.
            raw_text: Original raw data for truth verification and content recovery.
            regenerate_callback: Function to regenerate PDF from polished resume.
                                 Takes ResumeDocument, returns (tex_path, pdf_path).
            on_iteration: Optional callback for progress updates.

        Returns:
            RefinementResult with final grade and iteration history.

        Raises:
            RefinementError: If refinement fails critically.
        """
        iterations: list[RefinementIteration] = []
        current_resume = resume
        current_pdf = pdf_path
        stagnation_count = 0
        max_stagnation = 2
        last_grade_order = 0

        logger.info(
            "Starting adversarial refinement: target=%s, max_iterations=%d",
            target_grade.value,
            self._max_iterations,
        )

        for i in range(self._max_iterations):
            iteration_num = i + 1
            logger.info("Refinement iteration %d/%d", iteration_num, self._max_iterations)

            try:
                critique_result = self._critique.critique(current_pdf, raw_text)
            except CritiqueError as e:
                logger.error("Critique failed at iteration %d: %s", iteration_num, e)
                raise RefinementError(f"Critique failed: {e}") from e

            logger.info(
                "Critique grade: %s (content=%.0f%%, design=%.0f%%, ats=%.0f%%, truth=%.0f%%)",
                critique_result.grade.value,
                critique_result.content_score * 100,
                critique_result.design_score * 100,
                critique_result.ats_score * 100,
                critique_result.truthfulness_score * 100,
            )
            logger.debug("Critique justification: %s", critique_result.justification)
            logger.debug("Critique strengths: %s", critique_result.strengths)

            iteration = RefinementIteration(
                iteration=iteration_num,
                grade=critique_result.grade,
                critique=critique_result,
            )

            if tier_meets_target(critique_result.grade, target_grade):
                logger.info(
                    "Target grade %s achieved! Current: %s",
                    target_grade.value,
                    critique_result.grade.value,
                )
                iterations.append(iteration)
                if on_iteration:
                    on_iteration(iteration)
                return RefinementResult(
                    success=True,
                    final_grade=critique_result.grade,
                    target_grade=target_grade,
                    iterations=iterations,
                    final_resume=current_resume,
                    message=f"Target grade {target_grade.value} achieved in {iteration_num} iteration(s)",
                )

            if critique_result.max_achievable_grade is not None:
                if not tier_meets_target(critique_result.max_achievable_grade, target_grade):
                    logger.warning(
                        "Target %s declared unattainable. Max achievable: %s. Reason: %s",
                        target_grade.value,
                        critique_result.max_achievable_grade.value,
                        critique_result.grade_ceiling_reason,
                    )
                    iterations.append(iteration)
                    if on_iteration:
                        on_iteration(iteration)
                    return RefinementResult(
                        success=False,
                        final_grade=critique_result.grade,
                        target_grade=target_grade,
                        iterations=iterations,
                        final_resume=current_resume,
                        message=f"Target grade {target_grade.value} unattainable. Max achievable: {critique_result.max_achievable_grade.value}",
                        target_unattainable=True,
                        max_achievable_grade=critique_result.max_achievable_grade,
                        unattainable_reason=critique_result.grade_ceiling_reason,
                    )

            from resume_generator.config import TIER_GRADE_ORDER

            current_grade_order = TIER_GRADE_ORDER[critique_result.grade]
            if iteration_num > 1:
                if current_grade_order <= last_grade_order:
                    stagnation_count += 1
                    logger.info("Grade stagnation detected (%d/%d)", stagnation_count, max_stagnation)
                else:
                    stagnation_count = 0

                if stagnation_count >= max_stagnation:
                    logger.warning(
                        "Grade stagnation: no improvement after %d iterations. Stopping.",
                        max_stagnation,
                    )
                    iterations.append(iteration)
                    if on_iteration:
                        on_iteration(iteration)
                    return RefinementResult(
                        success=False,
                        final_grade=critique_result.grade,
                        target_grade=target_grade,
                        iterations=iterations,
                        final_resume=current_resume,
                        message=f"Grade stagnation after {iteration_num} iterations. Final: {critique_result.grade.value}",
                        target_unattainable=True,
                        max_achievable_grade=critique_result.grade,
                        unattainable_reason="Grade did not improve after multiple polish attempts",
                    )

            last_grade_order = current_grade_order

            if iteration_num == self._max_iterations:
                logger.warning(
                    "Max iterations reached without achieving target grade. Final: %s, Target: %s",
                    critique_result.grade.value,
                    target_grade.value,
                )
                iterations.append(iteration)
                if on_iteration:
                    on_iteration(iteration)
                return RefinementResult(
                    success=False,
                    final_grade=critique_result.grade,
                    target_grade=target_grade,
                    iterations=iterations,
                    final_resume=current_resume,
                    message=f"Max iterations reached. Final grade: {critique_result.grade.value}",
                )

            try:
                polish_result = self._polisher.polish(current_resume, critique_result, raw_text)
            except PolishError as e:
                logger.error("Polish failed at iteration %d: %s", iteration_num, e)
                raise RefinementError(f"Polish failed: {e}") from e

            logger.info(
                "Polish applied %d changes, addressed %d issues",
                len(polish_result.changes_made),
                len(polish_result.issues_addressed),
            )
            for change in polish_result.changes_made:
                logger.info("  Change: %s", change)

            iteration.polish_result = polish_result
            iterations.append(iteration)

            if on_iteration:
                on_iteration(iteration)

            current_resume = polish_result.resume

            if regenerate_callback:
                try:
                    _, current_pdf = regenerate_callback(current_resume)
                    logger.info("Regenerated PDF at: %s", current_pdf)
                except Exception as e:
                    logger.error("Failed to regenerate PDF: %s", e)
                    raise RefinementError(f"PDF regeneration failed: {e}") from e
            else:
                logger.warning(
                    "No regenerate_callback provided. Continuing with same PDF (grades may not improve)."
                )

        if iterations:
            grade_progression = " -> ".join(it.grade.value for it in iterations)
            logger.info("Refinement grade progression: %s", grade_progression)

        return RefinementResult(
            success=False,
            final_grade=iterations[-1].grade if iterations else target_grade,
            target_grade=target_grade,
            iterations=iterations,
            final_resume=current_resume,
            message="Refinement completed without achieving target grade",
        )

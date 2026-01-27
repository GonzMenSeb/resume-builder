"""Resume content optimization module using Claude AI."""

from resume_generator.optimization.optimizer import OptimizationError, ResumeOptimizer
from resume_generator.optimization.prompts import (
    ACHIEVEMENT_OPTIMIZER_SYSTEM,
    ACTION_VERBS_BY_CATEGORY,
    PROFESSIONAL_SUMMARY_SYSTEM,
    RESUME_OPTIMIZER_SYSTEM,
    build_achievement_optimization_prompt,
    build_bullet_batch_prompt,
    build_job_tailoring_prompt,
    build_professional_summary_prompt,
    build_skills_optimization_prompt,
)

__all__ = [
    "ACHIEVEMENT_OPTIMIZER_SYSTEM",
    "ACTION_VERBS_BY_CATEGORY",
    "OptimizationError",
    "PROFESSIONAL_SUMMARY_SYSTEM",
    "RESUME_OPTIMIZER_SYSTEM",
    "ResumeOptimizer",
    "build_achievement_optimization_prompt",
    "build_bullet_batch_prompt",
    "build_job_tailoring_prompt",
    "build_professional_summary_prompt",
    "build_skills_optimization_prompt",
]

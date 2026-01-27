"""S+ tier resume generator powered by Claude AI."""

__version__ = "0.1.0"
__author__ = "Sebastian"
__email__ = "sebastian@example.com"

from resume_generator.pipeline import PipelineError, PipelineResult, ResumePipeline

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "ResumePipeline",
    "PipelineResult",
    "PipelineError",
]

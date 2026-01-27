"""Data ingestion layer for extracting text from various input formats."""

from resume_generator.ingestion.base import BaseExtractor, ExtractionError, ExtractionResult

__all__ = ["BaseExtractor", "ExtractionError", "ExtractionResult"]

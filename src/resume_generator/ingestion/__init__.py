"""Data ingestion layer for extracting text from various input formats."""

from resume_generator.ingestion.base import BaseExtractor, ExtractionError, ExtractionResult
from resume_generator.ingestion.pdf import PDFExtractor
from resume_generator.ingestion.text import TextExtractor

__all__ = ["BaseExtractor", "ExtractionError", "ExtractionResult", "PDFExtractor", "TextExtractor"]

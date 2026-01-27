"""PDF text extraction using pypdf."""

from pathlib import Path

from pypdf import PdfReader

from resume_generator.ingestion.base import BaseExtractor, ExtractionError, ExtractionResult


class PDFExtractor(BaseExtractor):
    """Extracts text content from PDF files using pypdf."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".pdf"})

    def extract(self, path: Path) -> str:
        """Extract text from a PDF file.

        Args:
            path: Path to the PDF file.

        Returns:
            Extracted text with pages separated by double newlines.

        Raises:
            ExtractionError: If PDF cannot be read or parsed.
            FileNotFoundError: If the file does not exist.
        """
        self._validate_path(path)
        try:
            reader = PdfReader(path)
            pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as e:
            raise ExtractionError(path, str(e)) from e

    def extract_with_metadata(self, path: Path) -> ExtractionResult:
        """Extract text and PDF metadata.

        Args:
            path: Path to the PDF file.

        Returns:
            ExtractionResult with text and PDF document info.
        """
        self._validate_path(path)
        try:
            reader = PdfReader(path)
            pages: list[str] = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())

            text = "\n\n".join(pages)
            metadata: dict[str, str] = {"page_count": str(len(reader.pages))}

            if reader.metadata:
                if reader.metadata.title:
                    metadata["title"] = reader.metadata.title
                if reader.metadata.author:
                    metadata["author"] = reader.metadata.author
                if reader.metadata.creator:
                    metadata["creator"] = reader.metadata.creator

            return ExtractionResult(text=text, source_path=path, metadata=metadata)
        except Exception as e:
            raise ExtractionError(path, str(e)) from e

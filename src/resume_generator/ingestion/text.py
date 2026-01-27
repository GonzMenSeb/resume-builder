"""Text extraction for plain text and markdown files."""

from pathlib import Path

from resume_generator.ingestion.base import BaseExtractor, ExtractionError, ExtractionResult


class TextExtractor(BaseExtractor):
    """Extracts text content from plain text and markdown files."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".txt", ".md", ".markdown", ".text"})

    def extract(self, path: Path) -> str:
        """Extract text from a plain text or markdown file.

        Args:
            path: Path to the text file.

        Returns:
            File content as a string with normalized line endings.

        Raises:
            ExtractionError: If file cannot be read.
            FileNotFoundError: If the file does not exist.
        """
        self._validate_path(path)
        try:
            content = path.read_text(encoding="utf-8")
            return content.strip()
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="latin-1")
                return content.strip()
            except Exception as e:
                raise ExtractionError(path, f"Failed to decode file: {e}") from e
        except Exception as e:
            raise ExtractionError(path, str(e)) from e

    def extract_with_metadata(self, path: Path) -> ExtractionResult:
        """Extract text and file metadata.

        Args:
            path: Path to the text file.

        Returns:
            ExtractionResult with text and file info.
        """
        text = self.extract(path)
        metadata: dict[str, str] = {
            "file_type": path.suffix.lstrip(".") or "text",
            "file_size_bytes": str(path.stat().st_size),
        }
        return ExtractionResult(text=text, source_path=path, metadata=metadata)

    @staticmethod
    def from_raw_text(text: str, source_name: str = "raw_input") -> ExtractionResult:
        """Create an ExtractionResult from raw text input.

        Args:
            text: Raw text content.
            source_name: Identifier for the text source.

        Returns:
            ExtractionResult containing the processed text.
        """
        processed = text.strip()
        return ExtractionResult(
            text=processed,
            source_path=Path(source_name),
            metadata={"source_type": "raw_text"},
        )

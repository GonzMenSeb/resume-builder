"""Abstract base class for text extraction from various file formats."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


class ExtractionError(Exception):
    """Raised when text extraction fails."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        super().__init__(f"Failed to extract text from '{path}': {message}")


@dataclass
class ExtractionResult:
    """Result of a text extraction operation."""

    text: str
    source_path: Path
    char_count: int = field(init=False)
    word_count: int = field(init=False)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)
        self.word_count = len(self.text.split())

    @property
    def is_empty(self) -> bool:
        return self.char_count == 0


class BaseExtractor(ABC):
    """Abstract base class for text extractors."""

    @property
    @abstractmethod
    def supported_extensions(self) -> frozenset[str]:
        """Return the set of file extensions this extractor supports (e.g., {'.pdf', '.PDF'})."""
        ...

    def can_handle(self, path: Path) -> bool:
        """Check if this extractor can handle the given file."""
        return path.suffix.lower() in {ext.lower() for ext in self.supported_extensions}

    @abstractmethod
    def extract(self, path: Path) -> str:
        """Extract text content from the given file.

        Args:
            path: Path to the file to extract text from.

        Returns:
            Extracted text content as a string.

        Raises:
            ExtractionError: If extraction fails.
            FileNotFoundError: If the file does not exist.
        """
        ...

    def extract_with_metadata(self, path: Path) -> ExtractionResult:
        """Extract text and return with metadata.

        Args:
            path: Path to the file to extract text from.

        Returns:
            ExtractionResult containing text and metadata.
        """
        text = self.extract(path)
        return ExtractionResult(text=text, source_path=path)

    def _validate_path(self, path: Path) -> None:
        """Validate that the path exists and is a file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ExtractionError(path, "Path is not a file")
        if not self.can_handle(path):
            raise ExtractionError(
                path,
                f"Unsupported file type '{path.suffix}'. "
                f"Supported: {', '.join(sorted(self.supported_extensions))}",
            )

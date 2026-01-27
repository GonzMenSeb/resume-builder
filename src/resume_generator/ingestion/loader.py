"""Unified data loader that auto-detects file types and aggregates content from multiple sources."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from resume_generator.ingestion.base import BaseExtractor, ExtractionError, ExtractionResult
from resume_generator.ingestion.pdf import PDFExtractor
from resume_generator.ingestion.text import TextExtractor


@dataclass
class LoadResult:
    """Result of loading data from multiple sources."""

    unified_text: str
    sources: list[ExtractionResult] = field(default_factory=list)
    failed_sources: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return len(self.unified_text)

    @property
    def total_words(self) -> int:
        return len(self.unified_text.split())

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def has_failures(self) -> bool:
        return len(self.failed_sources) > 0


class DataLoader:
    """Loads and aggregates text content from multiple file types and sources."""

    def __init__(self) -> None:
        self._extractors: list[BaseExtractor] = [PDFExtractor(), TextExtractor()]

    def _get_extractor(self, path: Path) -> BaseExtractor | None:
        """Find an extractor that can handle the given file."""
        for extractor in self._extractors:
            if extractor.can_handle(path):
                return extractor
        return None

    @property
    def supported_extensions(self) -> frozenset[str]:
        """All file extensions supported by registered extractors."""
        extensions: set[str] = set()
        for extractor in self._extractors:
            extensions.update(extractor.supported_extensions)
        return frozenset(extensions)

    def can_handle(self, path: Path) -> bool:
        """Check if any extractor can handle the given file."""
        return self._get_extractor(path) is not None

    def _extract_file(self, path: Path) -> ExtractionResult:
        """Extract text from a single file using the appropriate extractor."""
        extractor = self._get_extractor(path)
        if extractor is None:
            raise ExtractionError(
                path, f"Unsupported file type '{path.suffix}'. Supported: {', '.join(sorted(self.supported_extensions))}"
            )
        return extractor.extract_with_metadata(path)

    def _collect_files(self, path: Path, recursive: bool = True) -> list[Path]:
        """Collect all supported files from a path (file or directory)."""
        if path.is_file():
            return [path] if self.can_handle(path) else []

        if not path.is_dir():
            return []

        pattern = "**/*" if recursive else "*"
        files: list[Path] = []
        for child in path.glob(pattern):
            if child.is_file() and self.can_handle(child):
                files.append(child)
        return sorted(files)

    def load(
        self,
        sources: Path | str | Sequence[Path | str],
        *,
        recursive: bool = True,
        separator: str = "\n\n---\n\n",
        skip_failures: bool = True,
    ) -> LoadResult:
        """Load and aggregate text from multiple sources.

        Args:
            sources: A file path, directory path, raw text string, or sequence of these.
            recursive: When loading directories, search recursively for files.
            separator: String to join content from multiple sources.
            skip_failures: If True, continue on extraction errors; otherwise raise.

        Returns:
            LoadResult with unified text and metadata about all sources.

        Raises:
            ExtractionError: If skip_failures is False and any extraction fails.
            FileNotFoundError: If a specified path does not exist.
        """
        if isinstance(sources, (str, Path)):
            sources = [sources]

        results: list[ExtractionResult] = []
        failures: list[tuple[Path, str]] = []

        for source in sources:
            if isinstance(source, str) and not Path(source).exists():
                result = TextExtractor.from_raw_text(source)
                results.append(result)
                continue

            path = Path(source) if isinstance(source, str) else source

            if not path.exists():
                if skip_failures:
                    failures.append((path, "File not found"))
                    continue
                raise FileNotFoundError(f"Source not found: {path}")

            files = self._collect_files(path, recursive=recursive)
            if not files and path.is_dir():
                failures.append((path, "No supported files found in directory"))
                continue

            for file_path in files:
                try:
                    result = self._extract_file(file_path)
                    if not result.is_empty:
                        results.append(result)
                except ExtractionError as e:
                    if skip_failures:
                        failures.append((file_path, str(e)))
                    else:
                        raise

        texts = [r.text for r in results]
        unified = separator.join(texts)

        return LoadResult(unified_text=unified, sources=results, failed_sources=failures)

    def load_single(self, path: Path | str) -> str:
        """Load text from a single file.

        Args:
            path: Path to the file to load.

        Returns:
            Extracted text content.

        Raises:
            ExtractionError: If extraction fails.
            FileNotFoundError: If the file does not exist.
        """
        p = Path(path) if isinstance(path, str) else path
        result = self._extract_file(p)
        return result.text

"""PDF compilation from LaTeX source using pdflatex."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompilationError:
    """Represents a LaTeX compilation error or warning."""

    message: str
    line: int | None = None
    file: str | None = None
    is_warning: bool = False

    def __str__(self) -> str:
        location = ""
        if self.file:
            location = f"{self.file}"
            if self.line:
                location += f":{self.line}"
            location += ": "
        prefix = "Warning" if self.is_warning else "Error"
        return f"{prefix}: {location}{self.message}"


@dataclass
class CompilationResult:
    """Result of a PDF compilation attempt."""

    success: bool
    pdf_path: Path | None = None
    errors: list[CompilationError] = field(default_factory=list)
    warnings: list[CompilationError] = field(default_factory=list)
    log_content: str = ""
    exit_code: int = 0
    page_count: int = 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class PDFCompiler:
    """Compiles LaTeX source to PDF using pdflatex."""

    AUX_EXTENSIONS = (
        ".aux",
        ".log",
        ".out",
        ".toc",
        ".lof",
        ".lot",
        ".bbl",
        ".blg",
        ".fls",
        ".fdb_latexmk",
    )

    ERROR_PATTERN = re.compile(r"^!\s*(.+)$", re.MULTILINE)
    LINE_PATTERN = re.compile(r"l\.(\d+)")
    WARNING_PATTERN = re.compile(
        r"^(LaTeX|Package|Class)\s+\w*\s*Warning:\s*(.+?)(?:\non input line (\d+))?\.?$",
        re.MULTILINE,
    )
    OVERFULL_PATTERN = re.compile(r"^(Overfull|Underfull)\s+\\[hv]box.+$", re.MULTILINE)

    def __init__(
        self,
        pdflatex_path: str | Path | None = None,
        compile_runs: int = 2,
        timeout: float = 60.0,
        clean_aux: bool = True,
    ) -> None:
        self._pdflatex = str(pdflatex_path) if pdflatex_path else self._find_pdflatex()
        self._compile_runs = max(1, min(compile_runs, 5))
        self._timeout = timeout
        self._clean_aux = clean_aux

    @staticmethod
    def _find_pdflatex() -> str:
        """Locate pdflatex binary on the system."""
        pdflatex = shutil.which("pdflatex")
        if pdflatex is None:
            raise RuntimeError(
                "pdflatex not found. Install a TeX distribution (e.g., texlive-latex-base)"
            )
        return pdflatex

    def compile(
        self,
        tex_source: str | Path,
        output_path: Path | None = None,
        work_dir: Path | None = None,
    ) -> CompilationResult:
        """
        Compile LaTeX source to PDF.

        Args:
            tex_source: Either a path to a .tex file or LaTeX source string
            output_path: Desired output PDF path (defaults to same name as input)
            work_dir: Working directory for compilation (temp dir if None)

        Returns:
            CompilationResult with success status, PDF path, and any errors
        """
        is_source_string = isinstance(tex_source, str) and not Path(tex_source).exists()
        use_temp_dir = work_dir is None

        if use_temp_dir:
            temp_dir = tempfile.mkdtemp(prefix="resume_compiler_")
            actual_work_dir = Path(temp_dir)
        else:
            actual_work_dir = Path(work_dir) if work_dir else Path.cwd()
            actual_work_dir.mkdir(parents=True, exist_ok=True)

        try:
            if is_source_string:
                tex_file = actual_work_dir / "resume.tex"
                tex_file.write_text(str(tex_source), encoding="utf-8")
            else:
                tex_file = Path(tex_source)
                if not tex_file.is_absolute():
                    tex_file = tex_file.resolve()

            result = self._run_compilation(tex_file, actual_work_dir)

            if result.success and output_path:
                compiled_pdf = actual_work_dir / tex_file.with_suffix(".pdf").name
                if compiled_pdf.exists():
                    output_path = Path(output_path).with_suffix(".pdf")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(compiled_pdf, output_path)
                    result.pdf_path = output_path

            return result

        finally:
            if use_temp_dir and self._clean_aux:
                shutil.rmtree(actual_work_dir, ignore_errors=True)

    async def compile_async(
        self,
        tex_source: str | Path,
        output_path: Path | None = None,
        work_dir: Path | None = None,
    ) -> CompilationResult:
        """Async version of compile()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.compile(tex_source, output_path, work_dir),
        )

    def _run_compilation(self, tex_file: Path, work_dir: Path) -> CompilationResult:
        """Execute pdflatex compilation passes."""
        log_content = ""
        exit_code = 0
        errors: list[CompilationError] = []
        warnings: list[CompilationError] = []

        env = os.environ.copy()
        env["TEXMFOUTPUT"] = str(work_dir)

        cmd = [
            self._pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-output-directory={work_dir}",
            str(tex_file),
        ]

        for run in range(self._compile_runs):
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout,
                    cwd=tex_file.parent,
                    env=env,
                )
                log_content = proc.stdout + proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                return CompilationResult(
                    success=False,
                    errors=[
                        CompilationError(
                            f"Compilation timed out after {self._timeout}s (run {run + 1})"
                        )
                    ],
                    exit_code=-1,
                )
            except FileNotFoundError:
                return CompilationResult(
                    success=False,
                    errors=[CompilationError(f"pdflatex not found at {self._pdflatex}")],
                    exit_code=-1,
                )

            if exit_code != 0 and run == self._compile_runs - 1:
                break

        log_file = work_dir / tex_file.with_suffix(".log").name
        if log_file.exists():
            log_content = log_file.read_text(encoding="utf-8", errors="replace")

        errors, warnings = self._parse_log(log_content, tex_file.name)

        pdf_path = work_dir / tex_file.with_suffix(".pdf").name
        success = exit_code == 0 and pdf_path.exists()

        page_count = 0
        if success and pdf_path.exists():
            page_count = self.count_pdf_pages(pdf_path)

        if self._clean_aux:
            self._cleanup_aux_files(work_dir, tex_file.stem)

        return CompilationResult(
            success=success,
            pdf_path=pdf_path if success else None,
            errors=errors,
            warnings=warnings,
            log_content=log_content,
            exit_code=exit_code,
            page_count=page_count,
        )

    def _parse_log(
        self, log: str, tex_name: str
    ) -> tuple[list[CompilationError], list[CompilationError]]:
        """Extract errors and warnings from pdflatex log output."""
        errors: list[CompilationError] = []
        warnings: list[CompilationError] = []

        for match in self.ERROR_PATTERN.finditer(log):
            msg = match.group(1).strip()
            line_num = None
            pos = match.end()
            context = log[pos : pos + 200]
            line_match = self.LINE_PATTERN.search(context)
            if line_match:
                line_num = int(line_match.group(1))
            errors.append(CompilationError(message=msg, line=line_num, file=tex_name))

        for match in self.WARNING_PATTERN.finditer(log):
            msg = match.group(2).strip()
            line_num = int(match.group(3)) if match.group(3) else None
            warnings.append(
                CompilationError(message=msg, line=line_num, file=tex_name, is_warning=True)
            )

        return errors, warnings

    def _cleanup_aux_files(self, work_dir: Path, stem: str) -> None:
        """Remove auxiliary files generated during compilation."""
        for ext in self.AUX_EXTENSIONS:
            aux_file = work_dir / f"{stem}{ext}"
            if aux_file.exists():
                aux_file.unlink(missing_ok=True)

    @staticmethod
    def check_dependencies() -> dict[str, bool]:
        """Check if required TeX packages are available."""
        packages = {
            "pdflatex": shutil.which("pdflatex") is not None,
            "fontenc": True,
            "geometry": True,
            "hyperref": True,
        }
        return packages

    @staticmethod
    def count_pdf_pages(pdf_path: Path) -> int:
        """Count pages in a PDF file using pdfinfo or regex fallback."""
        pdfinfo = shutil.which("pdfinfo")
        if pdfinfo:
            try:
                proc = subprocess.run(
                    [pdfinfo, str(pdf_path)],
                    capture_output=True,
                    text=True,
                    timeout=10.0,
                )
                for line in proc.stdout.splitlines():
                    if line.startswith("Pages:"):
                        return int(line.split(":")[1].strip())
            except (subprocess.TimeoutExpired, ValueError, IndexError):
                pass

        try:
            content = pdf_path.read_bytes()
            matches = re.findall(rb"/Type\s*/Page[^s]", content)
            return len(matches) if matches else 1
        except Exception:
            return 1

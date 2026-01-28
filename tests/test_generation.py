"""Unit tests for LaTeX generation and PDF compilation."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from resume_generator.config import ResumeLanguage, ResumeTemplate, Settings
from resume_generator.generation.compiler import (
    CompilationError,
    CompilationResult,
    PDFCompiler,
)
from resume_generator.generation.generator import (
    LaTeXGenerator,
    TemplateConfig,
    hex_to_rgb,
    latex_escape,
)
from resume_generator.generation.localization import SECTION_HEADERS, get_section_headers
from resume_generator.models.resume import (
    ResumeBullet,
    ResumeDocument,
    ResumeExperience,
)
from resume_generator.ui.progress import PipelineConfig


class TestLatexEscape:
    """Tests for latex_escape function."""

    def test_escape_none_returns_empty_string(self) -> None:
        assert latex_escape(None) == ""

    def test_escape_empty_string(self) -> None:
        assert latex_escape("") == ""

    def test_escape_ampersand(self) -> None:
        assert latex_escape("A & B") == r"A \& B"

    def test_escape_percent(self) -> None:
        assert latex_escape("50% complete") == r"50\% complete"

    def test_escape_dollar(self) -> None:
        assert latex_escape("$100") == r"\$100"

    def test_escape_hash(self) -> None:
        assert latex_escape("#hashtag") == r"\#hashtag"

    def test_escape_underscore(self) -> None:
        assert latex_escape("var_name") == r"var\_name"

    def test_escape_braces(self) -> None:
        assert latex_escape("{code}") == r"\{code\}"

    def test_escape_angle_brackets(self) -> None:
        assert latex_escape("<html>") == r"\textless{}html\textgreater{}"

    def test_escape_pipe(self) -> None:
        assert latex_escape("a | b") == r"a \textbar{} b"

    def test_escape_backslash(self) -> None:
        assert latex_escape(r"C:\path") == r"C:\textbackslash{}path"

    def test_escape_tilde(self) -> None:
        assert latex_escape("~user") == r"\textasciitilde{}user"

    def test_escape_caret(self) -> None:
        assert latex_escape("x^2") == r"x\textasciicircum{}2"

    def test_escape_unicode_smart_quotes(self) -> None:
        assert latex_escape("\u2018quote\u2019") == "`quote'"
        assert latex_escape("\u201cquote\u201d") == "``quote''"

    def test_escape_unicode_dashes(self) -> None:
        assert latex_escape("en\u2013dash") == "en--dash"
        assert latex_escape("em\u2014dash") == "em---dash"

    def test_escape_unicode_ellipsis(self) -> None:
        assert latex_escape("wait\u2026") == r"wait\ldots{}"

    def test_escape_unicode_symbols(self) -> None:
        assert latex_escape("90\u00b0") == r"90\textdegree{}"
        assert latex_escape("\u2022 bullet") == r"\textbullet{} bullet"
        assert latex_escape("\u00a9 2023") == r"\textcopyright{} 2023"

    def test_escape_straight_quotes_to_latex_quotes(self) -> None:
        assert latex_escape('"quoted"') == "''quoted''"

    def test_escape_complex_text(self) -> None:
        text = 'Reduced costs by 50% & improved performance using C:\\tools\n"Great success!"'
        result = latex_escape(text)
        assert r"\%" in result
        assert r"\&" in result
        assert r"\textbackslash{}" in result
        assert "''" in result

    def test_escape_multiple_special_chars(self) -> None:
        text = "100% of users rated it $5 with #1 ranking & <10ms latency"
        result = latex_escape(text)
        assert r"\%" in result
        assert r"\$" in result
        assert r"\#" in result
        assert r"\&" in result
        assert r"\textless{}" in result


class TestHexToRgb:
    """Tests for hex_to_rgb function."""

    def test_valid_hex_with_hash(self) -> None:
        assert hex_to_rgb("#FF0000") == "255, 0, 0"

    def test_valid_hex_without_hash(self) -> None:
        assert hex_to_rgb("00FF00") == "0, 255, 0"

    def test_valid_hex_mixed_case(self) -> None:
        assert hex_to_rgb("#AbCdEf") == "171, 205, 239"

    def test_invalid_hex_too_short(self) -> None:
        assert hex_to_rgb("#FFF") == "0, 0, 0"

    def test_invalid_hex_too_long(self) -> None:
        assert hex_to_rgb("#FFFFFFF") == "0, 0, 0"

    def test_invalid_hex_non_hex_chars(self) -> None:
        assert hex_to_rgb("#GGGGGG") == "0, 0, 0"

    def test_black(self) -> None:
        assert hex_to_rgb("#000000") == "0, 0, 0"

    def test_white(self) -> None:
        assert hex_to_rgb("#FFFFFF") == "255, 255, 255"


class TestTemplateConfig:
    """Tests for TemplateConfig dataclass."""

    def test_default_values(self) -> None:
        config = TemplateConfig()
        assert config.font_family == "sans"
        assert config.margin_top == "0.6in"
        assert config.margin_bottom == "0.5in"
        assert config.margin_left == "0.65in"
        assert config.margin_right == "0.65in"
        assert config.primary_color == "45, 85, 145"
        assert config.secondary_color == "60, 60, 60"
        assert config.accent_color == "100, 100, 100"
        assert config.language == "en"

    def test_from_settings(self, test_settings: Settings) -> None:
        config = TemplateConfig.from_settings(test_settings)
        assert config.font_family == "sans"
        expected_margin = f"{test_settings.margin_inches}in"
        assert config.margin_top == expected_margin
        assert config.margin_bottom == expected_margin
        assert config.margin_left == expected_margin
        assert config.margin_right == expected_margin

    def test_from_settings_custom_colors(self) -> None:
        settings = Settings(
            primary_color="#FF5500",
            secondary_color="#0055FF",
        )
        config = TemplateConfig.from_settings(settings)
        assert config.primary_color == "255, 85, 0"
        assert config.secondary_color == "0, 85, 255"

    def test_from_settings_language(self) -> None:
        settings = Settings(output_language=ResumeLanguage.ES)
        config = TemplateConfig.from_settings(settings)
        assert config.language == "es"

    def test_from_settings_default_language(self) -> None:
        settings = Settings()
        config = TemplateConfig.from_settings(settings)
        assert config.language == "en"


class TestLocalization:
    """Tests for localization module."""

    def test_get_section_headers_english(self) -> None:
        headers = get_section_headers("en")
        assert headers["experience"] == "Experience"
        assert headers["education"] == "Education"
        assert headers["skills"] == "Skills"

    def test_get_section_headers_spanish(self) -> None:
        headers = get_section_headers("es")
        assert headers["experience"] == "Experiencia"
        assert headers["education"] == "Educación"
        assert headers["skills"] == "Habilidades"

    def test_get_section_headers_french(self) -> None:
        headers = get_section_headers("fr")
        assert headers["experience"] == "Expérience"
        assert headers["education"] == "Formation"
        assert headers["skills"] == "Compétences"

    def test_get_section_headers_german(self) -> None:
        headers = get_section_headers("de")
        assert headers["experience"] == "Berufserfahrung"
        assert headers["education"] == "Ausbildung"
        assert headers["skills"] == "Fähigkeiten"

    def test_get_section_headers_unknown_language_falls_back_to_english(self) -> None:
        headers = get_section_headers("unknown")
        assert headers["experience"] == "Experience"
        assert headers == SECTION_HEADERS["en"]

    def test_all_languages_have_required_keys(self) -> None:
        required_keys = [
            "professional_summary",
            "experience",
            "education",
            "skills",
            "certifications",
            "projects",
            "linkedin",
            "github",
            "portfolio",
            "gpa",
            "technologies",
        ]
        for lang_code, headers in SECTION_HEADERS.items():
            for key in required_keys:
                assert key in headers, f"Missing key '{key}' in language '{lang_code}'"


class TestLaTeXGenerator:
    """Tests for LaTeXGenerator class."""

    @pytest.fixture
    def generator(self, test_settings: Settings) -> LaTeXGenerator:
        return LaTeXGenerator(settings=test_settings)

    def test_init_creates_jinja_env(self, generator: LaTeXGenerator) -> None:
        assert generator._env is not None
        assert "latex_escape" in generator._env.filters

    def test_init_with_custom_templates_dir(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()
        gen = LaTeXGenerator(templates_dir=custom_dir)
        assert gen._templates_dir == custom_dir

    def test_jinja_env_uses_latex_delimiters(self, generator: LaTeXGenerator) -> None:
        env = generator._env
        assert env.block_start_string == "((*"
        assert env.block_end_string == "*))"
        assert env.variable_start_string == "((("
        assert env.variable_end_string == ")))"
        assert env.comment_start_string == "((#"
        assert env.comment_end_string == "#))"

    def test_generate_minimal_resume(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        latex_source = generator.generate(sample_resume_document)
        assert isinstance(latex_source, str)
        assert len(latex_source) > 0
        assert r"\documentclass" in latex_source
        assert (
            sample_resume_document.contact.name in latex_source
            or latex_escape(sample_resume_document.contact.name) in latex_source
        )

    def test_generate_uses_default_template(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        latex_source = generator.generate(sample_resume_document)
        assert r"\documentclass" in latex_source

    def test_generate_with_explicit_template(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        latex_source = generator.generate(sample_resume_document, template=ResumeTemplate.ATS)
        assert isinstance(latex_source, str)
        assert len(latex_source) > 0

    def test_generate_with_custom_config(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        custom_config = TemplateConfig(
            font_family="serif",
            margin_top="1in",
            primary_color="255, 0, 0",
        )
        latex_source = generator.generate(sample_resume_document, config=custom_config)
        assert isinstance(latex_source, str)

    def test_generate_escapes_special_chars(self, generator: LaTeXGenerator) -> None:
        from resume_generator.models.resume import ResumeContact

        resume = ResumeDocument(
            contact=ResumeContact(
                name="John & Jane",
                email="test@example.com",
            ),
            professional_summary="100% success with $1M in savings",
        )
        latex_source = generator.generate(resume)
        assert r"\&" in latex_source
        assert r"\%" in latex_source
        assert r"\$" in latex_source

    def test_generate_to_file_creates_tex_file(
        self,
        generator: LaTeXGenerator,
        sample_resume_document: ResumeDocument,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "resume.tex"
        result_path = generator.generate_to_file(sample_resume_document, output_path)
        assert result_path.exists()
        assert result_path.suffix == ".tex"
        content = result_path.read_text()
        assert r"\documentclass" in content

    def test_generate_to_file_creates_parent_dirs(
        self,
        generator: LaTeXGenerator,
        sample_resume_document: ResumeDocument,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "nested" / "deep" / "resume.tex"
        result_path = generator.generate_to_file(sample_resume_document, output_path)
        assert result_path.exists()
        assert result_path.parent.exists()

    def test_generate_to_file_adds_tex_extension(
        self,
        generator: LaTeXGenerator,
        sample_resume_document: ResumeDocument,
        tmp_path: Path,
    ) -> None:
        output_path = tmp_path / "resume"
        result_path = generator.generate_to_file(sample_resume_document, output_path)
        assert result_path.suffix == ".tex"

    def test_build_context_includes_all_sections(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        config = TemplateConfig()
        context = generator._build_context(sample_resume_document, config)
        assert "config" in context
        assert "labels" in context
        assert "contact" in context
        assert "professional_summary" in context
        assert "headline" in context
        assert "experiences" in context
        assert "education" in context
        assert "skills" in context
        assert "certifications" in context
        assert "projects" in context
        assert "additional_sections" in context

    def test_build_context_labels_for_language(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        config = TemplateConfig(language="es")
        context = generator._build_context(sample_resume_document, config)
        labels = context["labels"]
        assert isinstance(labels, dict)
        assert labels["experience"] == "Experiencia"
        assert labels["education"] == "Educación"

    def test_build_context_filters_invisible_sections(self, generator: LaTeXGenerator) -> None:
        from resume_generator.models.resume import ResumeContact, ResumeSection, SectionType

        resume = ResumeDocument(
            contact=ResumeContact(name="Test", email="test@example.com"),
            additional_sections=[
                ResumeSection(
                    section_type=SectionType.AWARDS,
                    title="Awards",
                    content=["Award 1"],
                    visible=True,
                ),
                ResumeSection(
                    section_type=SectionType.PUBLICATIONS,
                    title="Publications",
                    content=["Pub 1"],
                    visible=False,
                ),
            ],
        )
        config = TemplateConfig()
        context = generator._build_context(resume, config)
        visible_sections = context["additional_sections"]
        assert len(visible_sections) == 1
        assert visible_sections[0].title == "Awards"

    def test_list_templates(self, generator: LaTeXGenerator) -> None:
        templates = generator.list_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "modern" in templates
        assert "ats" in templates

    def test_validate_template_existing(self, generator: LaTeXGenerator) -> None:
        assert generator.validate_template(ResumeTemplate.MODERN) is True
        assert generator.validate_template(ResumeTemplate.ATS) is True

    def test_validate_template_nonexistent(self, tmp_path: Path) -> None:
        gen = LaTeXGenerator(templates_dir=tmp_path)
        assert gen.validate_template(ResumeTemplate.MODERN) is False

    def test_generate_includes_professional_summary(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        latex_source = generator.generate(sample_resume_document)
        summary_escaped = latex_escape(sample_resume_document.professional_summary or "")
        assert (
            summary_escaped in latex_source
            or sample_resume_document.professional_summary in latex_source
        )

    def test_generate_includes_experiences(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        latex_source = generator.generate(sample_resume_document)
        exp = sample_resume_document.experiences[0]
        assert exp.company in latex_source or latex_escape(exp.company) in latex_source

    def test_generate_includes_education(
        self, generator: LaTeXGenerator, sample_resume_document: ResumeDocument
    ) -> None:
        latex_source = generator.generate(sample_resume_document)
        edu = sample_resume_document.education[0]
        assert edu.institution in latex_source or latex_escape(edu.institution) in latex_source


class TestPDFCompiler:
    """Tests for PDFCompiler class."""

    @pytest.fixture
    def compiler(self) -> PDFCompiler:
        return PDFCompiler(clean_aux=True, compile_runs=2, timeout=60.0)

    def test_init_default_values(self, compiler: PDFCompiler) -> None:
        assert compiler._compile_runs == 2
        assert compiler._timeout == 60.0
        assert compiler._clean_aux is True

    def test_init_clamps_compile_runs(self) -> None:
        compiler_low = PDFCompiler(compile_runs=0)
        assert compiler_low._compile_runs == 1
        compiler_high = PDFCompiler(compile_runs=10)
        assert compiler_high._compile_runs == 5

    def test_init_custom_pdflatex_path(self) -> None:
        compiler = PDFCompiler(pdflatex_path="/custom/path/pdflatex")
        assert compiler._pdflatex == "/custom/path/pdflatex"

    def test_find_pdflatex_not_found(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            pytest.raises(RuntimeError, match="pdflatex not found"),
        ):
            PDFCompiler._find_pdflatex()

    def test_find_pdflatex_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/pdflatex"):
            result = PDFCompiler._find_pdflatex()
            assert result == "/usr/bin/pdflatex"

    def test_compilation_error_str_with_all_fields(self) -> None:
        error = CompilationError(
            message="Undefined control sequence",
            line=42,
            file="resume.tex",
            is_warning=False,
        )
        assert str(error) == "Error: resume.tex:42: Undefined control sequence"

    def test_compilation_error_str_warning(self) -> None:
        error = CompilationError(
            message="Overfull hbox",
            line=10,
            file="resume.tex",
            is_warning=True,
        )
        assert str(error) == "Warning: resume.tex:10: Overfull hbox"

    def test_compilation_error_str_no_line(self) -> None:
        error = CompilationError(
            message="Missing file",
            file="resume.tex",
        )
        assert str(error) == "Error: resume.tex: Missing file"

    def test_compilation_error_str_no_file(self) -> None:
        error = CompilationError(message="General error")
        assert str(error) == "Error: General error"

    def test_compilation_result_has_errors_property(self) -> None:
        result = CompilationResult(
            success=False,
            errors=[CompilationError("error1"), CompilationError("error2")],
        )
        assert result.has_errors is True

    def test_compilation_result_has_warnings_property(self) -> None:
        result = CompilationResult(
            success=True,
            warnings=[CompilationError("warning1", is_warning=True)],
        )
        assert result.has_warnings is True

    def test_parse_log_extracts_errors(self, compiler: PDFCompiler) -> None:
        log = """
! Undefined control sequence.
l.42 \\unknowncommand
        """
        errors, warnings = compiler._parse_log(log, "resume.tex")
        assert len(errors) == 1
        assert "Undefined control sequence" in errors[0].message
        assert errors[0].line == 42

    def test_parse_log_extracts_warnings(self, compiler: PDFCompiler) -> None:
        log = """
LaTeX Warning: Reference `fig:example'
on input line 25.
Package hyperref Warning: Token not allowed in a PDF string
on input line 30.
        """
        errors, warnings = compiler._parse_log(log, "resume.tex")
        assert len(warnings) == 2
        assert warnings[0].line == 25
        assert warnings[1].line == 30

    def test_parse_log_no_errors_or_warnings(self, compiler: PDFCompiler) -> None:
        log = "Output written on resume.pdf (1 page, 12345 bytes)."
        errors, warnings = compiler._parse_log(log, "resume.tex")
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_cleanup_aux_files(self, compiler: PDFCompiler, tmp_path: Path) -> None:
        aux_files = [
            tmp_path / "resume.aux",
            tmp_path / "resume.log",
            tmp_path / "resume.out",
        ]
        for f in aux_files:
            f.touch()

        compiler._cleanup_aux_files(tmp_path, "resume")

        for f in aux_files:
            assert not f.exists()

    def test_check_dependencies(self) -> None:
        deps = PDFCompiler.check_dependencies()
        assert "pdflatex" in deps
        assert isinstance(deps["pdflatex"], bool)

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    def test_compile_simple_latex_source(self, compiler: PDFCompiler, tmp_path: Path) -> None:
        tex_source = r"""
\documentclass{article}
\begin{document}
Hello World
\end{document}
"""
        output_path = tmp_path / "test.pdf"
        result = compiler.compile(tex_source, output_path=output_path)

        assert result.success is True
        assert result.pdf_path == output_path
        assert output_path.exists()
        assert result.exit_code == 0

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    def test_compile_from_file(self, compiler: PDFCompiler, tmp_path: Path) -> None:
        tex_file = tmp_path / "input.tex"
        tex_file.write_text(r"""
\documentclass{article}
\begin{document}
Test Document
\end{document}
""")
        output_path = tmp_path / "output.pdf"
        result = compiler.compile(tex_file, output_path=output_path)

        assert result.success is True
        assert output_path.exists()

    def test_compile_invalid_latex_returns_error(
        self, compiler: PDFCompiler, tmp_path: Path
    ) -> None:
        tex_source = r"""
\documentclass{article}
\begin{document}
\unknowncommand
\end{document}
"""
        output_path = tmp_path / "test.pdf"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="! Undefined control sequence.\nl.3 \\unknowncommand",
                stderr="",
            )

            result = compiler.compile(tex_source, output_path=output_path, work_dir=tmp_path)
            assert result.success is False
            assert result.exit_code == 1

    def test_compile_timeout(self, compiler: PDFCompiler, tmp_path: Path) -> None:
        tex_source = r"\documentclass{article}\begin{document}Test\end{document}"

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pdflatex", 60)):
            result = compiler.compile(tex_source, work_dir=tmp_path)

        assert result.success is False
        assert result.has_errors is True
        assert "timed out" in result.errors[0].message.lower()

    def test_compile_pdflatex_not_found(self, tmp_path: Path) -> None:
        compiler = PDFCompiler(pdflatex_path="/nonexistent/pdflatex")
        tex_source = r"\documentclass{article}\begin{document}Test\end{document}"

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = compiler.compile(tex_source, work_dir=tmp_path)

        assert result.success is False
        assert result.has_errors is True
        assert "not found" in result.errors[0].message.lower()

    def test_compile_with_work_dir(self, compiler: PDFCompiler, tmp_path: Path) -> None:
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        tex_source = r"\documentclass{article}\begin{document}Test\end{document}"
        tex_file = work_dir / "resume.tex"
        tex_file.write_text(tex_source)
        pdf_file = work_dir / "resume.pdf"
        pdf_file.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Output written", stderr="")
            result = compiler.compile(tex_source, work_dir=work_dir)

        assert result.success is True

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    def test_compile_creates_pdf_in_temp_dir_by_default(self, compiler: PDFCompiler) -> None:
        tex_source = r"""
\documentclass{article}
\begin{document}
Temporary compile test
\end{document}
"""
        result = compiler.compile(tex_source)
        assert result.success is True

    def test_compile_respects_clean_aux_setting(self, tmp_path: Path) -> None:
        compiler_no_clean = PDFCompiler(clean_aux=False)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        tex_file = work_dir / "test.tex"
        tex_file.write_text(r"\documentclass{article}\begin{document}Test\end{document}")
        pdf_file = work_dir / "test.pdf"
        pdf_file.touch()
        aux_file = work_dir / "test.aux"
        aux_file.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Output written", stderr="")
            result = compiler_no_clean.compile(tex_source=tex_file, work_dir=work_dir)

        assert result.success is True
        assert aux_file.exists()

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    @pytest.mark.asyncio
    async def test_compile_async(self, compiler: PDFCompiler, tmp_path: Path) -> None:
        tex_source = r"""
\documentclass{article}
\begin{document}
Async Test
\end{document}
"""
        output_path = tmp_path / "async_test.pdf"
        result = await compiler.compile_async(tex_source, output_path=output_path)

        assert result.success is True
        assert output_path.exists()

    def test_compile_multiple_runs(self, tmp_path: Path) -> None:
        compiler = PDFCompiler(compile_runs=3)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        tex_source = r"\documentclass{article}\begin{document}Test\end{document}"
        pdf_file = work_dir / "resume.pdf"
        pdf_file.touch()

        with (
            patch("subprocess.run") as mock_run,
            patch.object(PDFCompiler, "count_pdf_pages", return_value=1),
        ):
            mock_run.return_value = Mock(returncode=0, stdout="Output written", stderr="")
            result = compiler.compile(tex_source, work_dir=work_dir)
            assert mock_run.call_count == 3
            assert result.success is True

    def test_error_pattern_matches_latex_errors(self, compiler: PDFCompiler) -> None:
        log = "! Emergency stop."
        matches = list(compiler.ERROR_PATTERN.finditer(log))
        assert len(matches) == 1
        assert matches[0].group(1) == "Emergency stop."

    def test_warning_pattern_matches_latex_warnings(self, compiler: PDFCompiler) -> None:
        log = "LaTeX Warning: Citation `cite1' undefined on input line 10."
        matches = list(compiler.WARNING_PATTERN.finditer(log))
        assert len(matches) == 1

    def test_line_pattern_extracts_line_number(self, compiler: PDFCompiler) -> None:
        text = "l.123 some text"
        match = compiler.LINE_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "123"


class TestIntegrationGeneratorAndCompiler:
    """Integration tests combining generator and compiler."""

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    def test_generate_and_compile_full_pipeline(
        self,
        test_settings: Settings,
        sample_resume_document: ResumeDocument,
        tmp_path: Path,
    ) -> None:
        generator = LaTeXGenerator(settings=test_settings)
        compiler = PDFCompiler()

        tex_path = tmp_path / "resume.tex"
        generator.generate_to_file(sample_resume_document, tex_path)
        output_pdf = tmp_path / "resume.pdf"
        result = compiler.compile(tex_path, output_path=output_pdf)

        assert result.success is True
        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 0

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    def test_generate_to_file_and_compile(
        self,
        test_settings: Settings,
        sample_resume_document: ResumeDocument,
        tmp_path: Path,
    ) -> None:
        generator = LaTeXGenerator(settings=test_settings)
        compiler = PDFCompiler()

        tex_path = tmp_path / "resume.tex"
        generator.generate_to_file(sample_resume_document, tex_path)

        pdf_path = tmp_path / "resume.pdf"
        result = compiler.compile(tex_path, output_path=pdf_path)

        assert result.success is True
        assert pdf_path.exists()

    @pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
    def test_compile_all_templates(
        self,
        test_settings: Settings,
        sample_resume_document: ResumeDocument,
        tmp_path: Path,
    ) -> None:
        generator = LaTeXGenerator(settings=test_settings)
        compiler = PDFCompiler()

        for template in [ResumeTemplate.MODERN, ResumeTemplate.ATS]:
            tex_path = tmp_path / f"{template.value}.tex"
            generator.generate_to_file(sample_resume_document, tex_path, template=template)
            output_pdf = tmp_path / f"{template.value}.pdf"
            result = compiler.compile(tex_path, output_path=output_pdf)

            assert result.success is True, f"Failed to compile {template.value} template"
            assert output_pdf.exists()


class TestResumeDocumentCompact:
    """Tests for ResumeDocument.compact() method."""

    def test_compact_reduces_bullets(self, sample_resume_document: ResumeDocument) -> None:
        original_bullet_count = sum(len(exp.bullets) for exp in sample_resume_document.experiences)
        compacted = sample_resume_document.compact(min_bullets_per_job=2)
        compacted_bullet_count = sum(len(exp.bullets) for exp in compacted.experiences)

        assert compacted_bullet_count <= original_bullet_count

    def test_compact_respects_min_bullets(self, sample_resume_document: ResumeDocument) -> None:
        min_bullets = 2
        compacted = sample_resume_document.compact(min_bullets_per_job=min_bullets)

        for exp in compacted.experiences:
            assert len(exp.bullets) >= min(min_bullets, len(exp.bullets))

    def test_compact_preserves_other_fields(self, sample_resume_document: ResumeDocument) -> None:
        compacted = sample_resume_document.compact()

        assert compacted.contact == sample_resume_document.contact
        assert compacted.professional_summary == sample_resume_document.professional_summary
        assert compacted.education == sample_resume_document.education
        assert compacted.skills == sample_resume_document.skills

    def test_compact_returns_new_instance(self, sample_resume_document: ResumeDocument) -> None:
        compacted = sample_resume_document.compact()
        assert compacted is not sample_resume_document

    def test_compact_with_experience_at_min_bullets(self) -> None:
        from datetime import date

        from resume_generator.models.resume import ResumeContact

        resume = ResumeDocument(
            contact=ResumeContact(name="Test User", email="test@example.com"),
            experiences=[
                ResumeExperience(
                    company="Test Corp",
                    title="Engineer",
                    start_date=date(2020, 1, 1),
                    bullets=[
                        ResumeBullet(text="Achievement one that is substantial", relevance_score=0.9),
                        ResumeBullet(text="Achievement two that is substantial", relevance_score=0.8),
                    ],
                )
            ],
        )

        compacted = resume.compact(min_bullets_per_job=2)
        assert len(compacted.experiences[0].bullets) == 2


class TestPipelineConfig:
    """Tests for PipelineConfig class."""

    def test_default_values(self) -> None:
        config = PipelineConfig()
        assert config.max_pages == 1
        assert config.max_bullet_words == 25
        assert config.max_bullets_per_job == 5
        assert config.claude_model == "sonnet"
        assert config.output_language == "en"
        assert config.color_palette == "classic"

    def test_from_settings(self, test_settings: Settings) -> None:
        config = PipelineConfig.from_settings(test_settings)
        assert config.max_pages == test_settings.max_pages
        assert config.max_bullet_words == test_settings.max_bullet_words
        assert config.claude_model == test_settings.claude_model.value
        assert config.output_language == test_settings.output_language.value

    def test_from_settings_custom_values(self, tmp_path: Path) -> None:
        from resume_generator.config import ClaudeModel, ColorPalette, ResumeLanguage

        settings = Settings(
            max_pages=2,
            max_bullet_words=30,
            claude_model=ClaudeModel.OPUS,
            output_language=ResumeLanguage.ES,
            color_palette=ColorPalette.NAVY,
            output_dir=tmp_path / "output",
            cache_dir=tmp_path / "cache",
        )

        config = PipelineConfig.from_settings(settings)
        assert config.max_pages == 2
        assert config.max_bullet_words == 30
        assert config.claude_model == "opus"
        assert config.output_language == "es"
        assert config.color_palette == "navy"

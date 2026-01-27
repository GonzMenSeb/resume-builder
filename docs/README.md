# Resume Generator Documentation

Welcome to the comprehensive documentation for Resume Generator - an S+ tier resume generation tool powered by Claude AI.

## Quick Links

- [Main README](../README.md) - Project overview and quick start
- [CHANGELOG](../CHANGELOG.md) - Version history and changes
- [LICENSE](../LICENSE) - MIT License
- [CODE OF CONDUCT](../CODE_OF_CONDUCT.md) - Community guidelines

## Documentation Sections

### Getting Started

Start here if you're new to Resume Generator.

#### [Installation & Quick Start](../README.md#quick-start)
- Prerequisites and requirements
- Installation steps
- Basic usage example
- First resume generation

### User Guides

Step-by-step guides for common tasks.

#### [CLI Guide](./CLI_GUIDE.md)
Complete command-line reference including:
- All command options and flags
- Usage examples
- Job tailoring workflows
- Troubleshooting tips
- Shell integration

#### [Configuration Guide](./CONFIGURATION.md)
Comprehensive configuration reference:
- All environment variables
- Settings with defaults and ranges
- Configuration profiles
- Best practices
- Template customization

#### [Examples](./EXAMPLES.md)
Real-world usage examples:
- Basic generation workflows
- Job tailoring scenarios
- Python API usage
- Advanced integrations
- Common patterns

### Technical Documentation

For developers and advanced users.

#### [Architecture](./ARCHITECTURE.md)
System design and implementation:
- Component overview with diagrams
- Pipeline stages and data flow
- Design patterns
- Technology stack
- Extension points
- Performance considerations

#### [API Reference](./API_REFERENCE.md)
Python API documentation:
- Core classes and methods
- Data models
- Type annotations
- Error handling
- Advanced usage patterns

### Contributing

#### [Contributing Guide](./CONTRIBUTING.md)
How to contribute:
- Development setup
- Coding standards
- Testing requirements
- Pull request process
- Areas needing help

## Documentation by Task

### I want to...

#### Generate my first resume
1. Read [Installation](../README.md#installation)
2. Follow [Quick Start](../README.md#quick-start)
3. Try [Basic Examples](./CLI_GUIDE.md#basic-examples)

#### Tailor resume to a job
1. Review [Job Tailoring Options](./CLI_GUIDE.md#job-tailoring-options)
2. See [Job Tailoring Examples](./EXAMPLES.md#job-tailoring)
3. Understand [Tailoring Settings](./CONFIGURATION.md#content-optimization)

#### Use the Python API
1. Read [API Reference](./API_REFERENCE.md)
2. Try [API Examples](./EXAMPLES.md#api-usage)
3. Review [Data Models](./API_REFERENCE.md#data-models)

#### Customize templates
1. Check [Template Configuration](./CONFIGURATION.md#template--design-configuration)
2. See [Template Examples](./EXAMPLES.md#template-customization)
3. Review [Template Architecture](./ARCHITECTURE.md#generation-layer)

#### Troubleshoot issues
1. Check [CLI Troubleshooting](./CLI_GUIDE.md#troubleshooting)
2. Review [Configuration](./CONFIGURATION.md#troubleshooting)
3. Search [GitHub Issues](https://github.com/sebastian/resume-generator/issues)

#### Contribute to the project
1. Read [Contributing Guide](./CONTRIBUTING.md)
2. Review [Code of Conduct](../CODE_OF_CONDUCT.md)
3. Check [Development Setup](./CONTRIBUTING.md#development-setup)

## Architecture at a Glance

```
Input (PDF/TXT/MD)
      ↓
   Loading
      ↓
  Extraction (Claude AI)
      ↓
 Optimization (X-Y-Z)
      ↓
  Tailoring (Job-specific)
      ↓
  Generation (LaTeX)
      ↓
  Compilation (PDF)
      ↓
   Output (PDF)
```

See [Architecture](./ARCHITECTURE.md) for detailed system design.

## Key Features

### For Users
- **Multi-format Input**: PDF, text, markdown support
- **AI-Powered**: Claude AI extraction and optimization
- **Job Tailoring**: Optimize for specific positions
- **Professional Templates**: Modern and ATS-friendly designs
- **Beautiful UI**: Real-time progress tracking

### For Developers
- **Type-Safe**: Full mypy/pyright support
- **Async Support**: Non-blocking pipeline execution
- **Well-Tested**: Comprehensive test suite
- **Documented**: Extensive API documentation
- **Extensible**: Plugin-friendly architecture

## Configuration Quick Reference

### Essential Settings

```bash
# Claude CLI Configuration
RESUME_GEN_CLAUDE_MODEL=sonnet
RESUME_GEN_CLAUDE_CLI_TIMEOUT=3600

# Commonly Customized
RESUME_GEN_DEFAULT_TEMPLATE=modern      # or 'ats'
RESUME_GEN_PRIMARY_COLOR=#2C3E50
RESUME_GEN_COMPILE_PDF=true
RESUME_GEN_VERBOSE=false
```

See [Configuration Guide](./CONFIGURATION.md) for all options.

## CLI Quick Reference

### Basic Commands

```bash
# Generate from PDF
resume-gen generate resume.pdf

# With job tailoring
resume-gen generate resume.pdf --job-file job.txt

# Custom output
resume-gen generate resume.pdf -o my_resume.pdf

# Use ATS template
resume-gen generate resume.pdf -t ats

# Verbose mode
resume-gen generate resume.pdf -v
```

See [CLI Guide](./CLI_GUIDE.md) for complete reference.

## API Quick Reference

### Basic Usage

```python
from resume_generator import ResumePipeline

pipeline = ResumePipeline()
result = pipeline.run(sources=["resume.pdf"])

if result.success:
    print(f"Generated: {result.output_path}")
```

### With Job Tailoring

```python
from resume_generator.models.job import JobDescription

job = JobDescription(
    title="Senior Developer",
    raw_text="Job requirements..."
)

result = pipeline.run(
    sources=["resume.pdf"],
    job=job
)
```

See [API Reference](./API_REFERENCE.md) for complete documentation.

## Support & Community

### Getting Help

- **Documentation**: You're here!
- **Issues**: [GitHub Issues](https://github.com/sebastian/resume-generator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sebastian/resume-generator/discussions)

### Reporting Issues

When reporting issues, include:
1. Resume Generator version (`resume-gen --version`)
2. Python version (`python --version`)
3. Operating system
4. Full error message
5. Steps to reproduce

See [Contributing Guide](./CONTRIBUTING.md#reporting-bugs) for details.

### Feature Requests

We welcome feature requests! Please:
1. Check existing issues first
2. Describe the use case
3. Explain the desired behavior
4. Provide examples if possible

See [Contributing Guide](./CONTRIBUTING.md#suggesting-enhancements).

## Development

### Quick Start

```bash
git clone https://github.com/sebastian/resume-generator.git
cd resume-generator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

See [Contributing Guide](./CONTRIBUTING.md#development-setup) for details.

### Project Structure

```
resume-generator/
├── src/resume_generator/    # Source code
│   ├── ingestion/           # Input processing
│   ├── extraction/          # AI extraction
│   ├── optimization/        # Content optimization
│   ├── generation/          # LaTeX/PDF generation
│   ├── models/             # Data models
│   └── ui/                 # Terminal UI
├── tests/                   # Test suite
├── docs/                    # Documentation
├── examples/                # Example inputs
└── templates/               # LaTeX templates
```

See [Architecture](./ARCHITECTURE.md#project-structure) for details.

## Frequently Asked Questions

### General

**Q: What file formats are supported?**
A: PDF, TXT, MD files, and directories containing these files.

**Q: Do I need an Anthropic API key?**
A: Yes, for profile extraction and optimization.

**Q: Can I use without internet?**
A: No, Claude AI requires internet connection.

**Q: Is my data stored anywhere?**
A: Only locally unless you enable caching. No data is sent to third parties.

### Technical

**Q: Which Python versions are supported?**
A: Python 3.11 and higher.

**Q: Can I run without pdflatex?**
A: Yes, use `--no-compile` to generate LaTeX only.

**Q: How do I customize templates?**
A: See [Template Configuration](./CONFIGURATION.md#template--design-configuration).

**Q: Is there a web interface?**
A: Not yet, but it's on the [roadmap](../CHANGELOG.md#future-roadmap).

### Usage

**Q: How long does generation take?**
A: Typically 20-30 seconds end-to-end.

**Q: What's the keyword match rate?**
A: Percentage of job keywords present in your resume (target: 65-75%).

**Q: Should I use modern or ATS template?**
A: ATS for online applications, modern for direct submissions.

## Version History

- **v0.1.0** (2026-01-27): Initial release
- See [CHANGELOG](../CHANGELOG.md) for complete history

## Roadmap

### Near Future (v0.2.0)
- Additional templates
- Resume analytics
- Export to DOCX/HTML

### Long Term (v1.0.0)
- Web interface
- Multi-language support
- Enterprise features

See [CHANGELOG](../CHANGELOG.md#future-roadmap) for details.

## License

Resume Generator is released under the [MIT License](../LICENSE).

## Acknowledgments

- Powered by [Anthropic Claude](https://www.anthropic.com/claude)
- Built with Python, Pydantic, Rich, and LaTeX
- Inspired by resume best practices and ATS optimization research

## Contributing

We welcome contributions! Please read:
1. [Contributing Guide](./CONTRIBUTING.md)
2. [Code of Conduct](../CODE_OF_CONDUCT.md)

## Questions?

- Email: sebastian@example.com
- GitHub: [@sebastian](https://github.com/sebastian)
- Issues: [GitHub Issues](https://github.com/sebastian/resume-generator/issues)

---

**Thank you for using Resume Generator!** 🚀

For updates and announcements, watch the [GitHub repository](https://github.com/sebastian/resume-generator).

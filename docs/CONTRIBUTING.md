# Contributing to Resume Generator

Thank you for considering contributing to Resume Generator! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- pdflatex (for PDF compilation)
- Anthropic API key (for testing)

### First-Time Contributors

Look for issues tagged with:
- `good first issue` - Great for newcomers
- `help wanted` - Community help needed
- `documentation` - Documentation improvements

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/resume-generator.git
cd resume-generator
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- Core dependencies
- Development tools (pytest, mypy, ruff, etc.)
- Pre-commit hooks

### 4. Configure Environment

Ensure Claude CLI is installed, then create `.env` file:

```bash
RESUME_GEN_CLAUDE_MODEL=sonnet
RESUME_GEN_VERBOSE=true
```

### 5. Verify Setup

```bash
# Run tests
pytest

# Run type checking
mypy src/

# Run linting
ruff check src/
```

If all pass, you're ready to contribute!

## How to Contribute

### Reporting Bugs

**Before submitting:**
1. Check existing issues
2. Verify it's not already fixed in main branch
3. Collect relevant information

**Bug Report Template:**

```markdown
## Bug Description
Clear description of the bug.

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.5]
- Resume Generator version: [e.g., 0.1.0]

## Additional Context
Any other relevant information.
```

### Suggesting Enhancements

**Enhancement Request Template:**

```markdown
## Feature Description
Clear description of the proposed feature.

## Motivation
Why is this feature needed?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Other approaches you've considered.

## Additional Context
Examples, mockups, or references.
```

### Contributing Code

1. **Create a Branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test improvements

2. **Make Changes**

- Write clean, readable code
- Follow coding standards (see below)
- Add tests for new features
- Update documentation

3. **Test Your Changes**

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_pipeline.py

# With coverage
pytest --cov=resume_generator --cov-report=html

# Type checking
mypy src/
pyright src/

# Linting
ruff check src/
```

4. **Commit Your Changes**

```bash
git add .
git commit -m "feat: Add new template system"
```

Commit message format:
```
type: Brief description

Detailed explanation (optional)

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `style`: Code formatting
- `chore`: Maintenance

5. **Push and Create Pull Request**

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Coding Standards

### Python Style

We follow PEP 8 with these tools:

- **Linting:** ruff (strict mode)
- **Formatting:** ruff format
- **Type Checking:** mypy (strict) + pyright

### Code Quality Checklist

- [ ] Follows PEP 8 style guide
- [ ] Has type hints on all functions
- [ ] Includes docstrings for public APIs
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] Passes all linters
- [ ] Passes type checking

### Type Hints

**Required** for all function signatures:

```python
# Good
def process_resume(
    data: str,
    output_path: Path,
    settings: Settings | None = None,
) -> PipelineResult:
    ...

# Bad (missing types)
def process_resume(data, output_path, settings=None):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def extract_profile(text: str, model: str) -> PersonProfile:
    """Extract structured profile from raw text.

    Args:
        text: Raw text containing profile information.
        model: Claude model ID to use.

    Returns:
        Structured PersonProfile object.

    Raises:
        ExtractionError: If extraction fails.

    Example:
        >>> profile = extract_profile(text, "claude-sonnet-4")
        >>> print(profile.name)
        'John Doe'
    """
    ...
```

### Error Handling

```python
# Good - Specific exceptions with context
try:
    result = api_call()
except APIError as e:
    raise ExtractionError(f"Failed to extract profile: {e}") from e

# Bad - Bare except
try:
    result = api_call()
except:
    pass
```

### Code Organization

```python
# Module structure
"""Module docstring."""

# Imports
from __future__ import annotations

import standard_library
from typing import TYPE_CHECKING

import third_party

from resume_generator import local_module

if TYPE_CHECKING:
    from collections.abc import Sequence

# Constants
DEFAULT_TIMEOUT = 3600

# Classes and functions
class MyClass:
    ...

def my_function():
    ...
```

## Testing

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── test_extraction.py
│   └── test_optimization.py
├── integration/       # Integration tests
│   └── test_pipeline.py
└── e2e/              # End-to-end tests
    └── test_full_generation.py
```

### Writing Tests

```python
import pytest
from resume_generator import ResumePipeline

def test_pipeline_basic_generation(tmp_path):
    """Test basic resume generation without job tailoring."""
    # Arrange
    input_file = tmp_path / "resume.txt"
    input_file.write_text("John Doe\nSoftware Engineer")
    output_file = tmp_path / "output.pdf"

    # Act
    pipeline = ResumePipeline()
    result = pipeline.run(
        sources=[input_file],
        output_path=output_file
    )

    # Assert
    assert result.success
    assert output_file.exists()
    assert result.optimization_score > 0


@pytest.mark.asyncio
async def test_async_pipeline():
    """Test asynchronous pipeline execution."""
    pipeline = ResumePipeline()
    result = await pipeline.run_async(sources=["resume.pdf"])
    assert result.success
```

### Test Coverage

Aim for:
- Overall: >80%
- New features: 100%
- Critical paths: 100%

Check coverage:
```bash
pytest --cov=resume_generator --cov-report=html
open htmlcov/index.html
```

### Mocking

Use `unittest.mock` for external dependencies:

```python
from unittest.mock import Mock, patch

@patch('resume_generator.extraction.profile.anthropic.Anthropic')
def test_extraction_with_mock(mock_anthropic):
    mock_client = Mock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.return_value = Mock(
        content=[Mock(text='{"name": "John Doe"}')]
    )

    extractor = ProfileExtractor(settings)
    profile = extractor.extract("John Doe\nSoftware Engineer")

    assert profile.name == "John Doe"
    mock_client.messages.create.assert_called_once()
```

## Pull Request Process

### Before Submitting

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Run full test suite**
4. **Check code quality**
5. **Update CHANGELOG.md** (see below)

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed.

## Checklist
- [ ] Tests pass locally
- [ ] Added tests for new features
- [ ] Updated documentation
- [ ] Code follows style guidelines
- [ ] Type checking passes
- [ ] Updated CHANGELOG.md

## Related Issues
Fixes #123
Closes #456
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainer
3. **Discussion** and feedback
4. **Approval** and merge

### After Merge

- Your contribution will be in the next release
- You'll be added to contributors list
- Thank you! 🎉

## Release Process

### Version Numbers

We use Semantic Versioning (SemVer):

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features (e.g., 1.0.0 → 1.1.0)
- **PATCH**: Bug fixes (e.g., 1.0.0 → 1.0.1)

### Changelog Format

Update `CHANGELOG.md`:

```markdown
## [0.2.0] - 2026-01-28

### Added
- New ATS-optimized template
- Support for multiple input directories

### Changed
- Improved bullet point optimization algorithm
- Updated default Claude model to Sonnet 4

### Fixed
- PDF compilation error with special characters
- Memory leak in large file processing

### Deprecated
- Old `generate()` method (use `run()` instead)

### Removed
- Legacy template system

### Security
- Updated dependencies with security patches
```

## Development Workflow

### Daily Development

```bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-feature

# Make changes, test, commit
# ... code ...
pytest
git commit -m "feat: Add feature"

# Push and create PR
git push origin feature/my-feature
```

### Code Review Feedback

```bash
# Address feedback
# ... make changes ...

# Amend commit or create new one
git commit -m "fix: Address review feedback"

# Force push if amended
git push origin feature/my-feature
```

## Project Structure

```
resume-generator/
├── src/resume_generator/
│   ├── ingestion/          # Input file processing
│   ├── extraction/         # AI profile extraction
│   ├── optimization/       # Content optimization
│   ├── generation/         # LaTeX/PDF generation
│   ├── models/            # Data models
│   ├── ui/                # Terminal UI
│   ├── config.py          # Configuration
│   ├── pipeline.py        # Main pipeline
│   └── main.py            # CLI entry point
├── tests/                 # Test suite
├── docs/                  # Documentation
├── examples/              # Example files
├── pyproject.toml         # Project config
└── README.md             # Main readme
```

## Areas Needing Help

### High Priority

- [ ] Additional LaTeX templates
- [ ] Performance optimization
- [ ] Better error messages
- [ ] More comprehensive tests

### Medium Priority

- [ ] Web interface
- [ ] Multi-language support
- [ ] Resume version control
- [ ] Analytics and metrics

### Documentation

- [ ] Video tutorials
- [ ] More examples
- [ ] API cookbook
- [ ] Template customization guide

## Questions?

- **GitHub Issues**: For bugs and features
- **GitHub Discussions**: For questions and ideas
- **Email**: sebastian@example.com

## Recognition

Contributors are recognized in:
- GitHub contributors page
- CHANGELOG.md
- README.md (for significant contributions)

Thank you for contributing to Resume Generator! 🚀

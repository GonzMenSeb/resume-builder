# Example Input Files

This directory contains example input files demonstrating the resume generator's ability to ingest raw data in various formats.

## Files

### 1. `data_scientist_raw.txt`
A plain text format with raw professional information about a Data Scientist. Includes:
- Contact information
- Work experience with quantified achievements
- Technical skills
- Education
- Certifications

**Usage:** `resume-gen generate examples/data_scientist_raw.txt`

### 2. `fullstack_developer.md`
Markdown format with structured information about a Full-Stack Developer. Demonstrates:
- Markdown formatting with headers and bullet points
- Multiple projects and experiences
- Technology stack listing
- Award and publication mentions

**Usage:** `resume-gen generate examples/fullstack_developer.md`

### 3. `product_manager_notes.txt`
Product Manager unstructured notes format showing:
- Mixed content types
- Narrative-style achievements
- Business metrics
- Cross-functional collaboration examples

**Usage:** `resume-gen generate examples/product_manager_notes.txt`

### 4. `DevOps_Engineer.md`
Markdown document of a DevOps/Infrastructure engineer with:
- Infrastructure and automation achievements
- Cloud platform expertise
- CI/CD pipeline implementation
- Security and compliance work

**Usage:** `resume-gen generate examples/DevOps_Engineer.md`

### 5. `UX_Designer.txt`
Plain text format for a UX Designer including:
- Design methodology and processes
- Project portfolio descriptions
- User research and testing metrics
- Design tools and frameworks

**Usage:** `resume-gen generate examples/UX_Designer.txt`

## Quick Start

Generate a resume from an example:
```bash
resume-gen generate examples/data_scientist_raw.txt --output my_resume.pdf
```

Generate with job tailoring:
```bash
resume-gen generate examples/fullstack_developer.md \
  --job-description "Senior Full Stack Engineer at TechCorp" \
  --output tailored_resume.pdf
```

Batch process multiple files:
```bash
resume-gen generate examples/ --output batch_results/
```

## File Format Notes

- **Plain Text (.txt)**: Use for completely unstructured data. The system will parse naturally.
- **Markdown (.md)**: Use for semi-structured data with section headers and bullet points.
- **PDF files**: Can be directly processed if you have actual PDF resumes.

The system automatically detects the format and applies appropriate parsing.

## Example Content

Each file contains realistic professional information including:
- Professional titles and company names
- Verified metrics and achievements
- Industry-relevant technical skills
- Proper date formats (ISO 8601)
- Contact information (public formats only)

These examples are designed to showcase the resume generator's ability to:
1. Parse diverse input formats
2. Extract structured data from unstructured text
3. Preserve factual content while enhancing presentation
4. Generate ATS-compliant resumes

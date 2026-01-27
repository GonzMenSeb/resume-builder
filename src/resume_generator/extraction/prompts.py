"""Prompt templates for extracting structured profile data from raw text."""

from typing import Any

from resume_generator.models.profile import PersonProfile

PROFILE_EXTRACTION_SYSTEM = """\
You are an expert resume data extractor. Your task is to parse raw text containing a person's \
professional information and extract it into a structured JSON format.

## Core Extraction Principles

1. **Accuracy First**: Extract only information explicitly stated. Never infer or fabricate data.
2. **Preserve Fidelity**: Keep achievements, metrics, and descriptions verbatim when possible.
3. **Complete Coverage**: Extract every relevant piece of information from the source.
4. **Proper Categorization**: Skills, experiences, and achievements must go in appropriate fields.

## Field-Specific Guidelines

### Contact Information
- Extract full name exactly as written (do not reformat or assume name order).
- Phone numbers: include country code if present; preserve original formatting.
- Email: extract exactly as written.
- URLs: preserve complete URLs for LinkedIn, GitHub, portfolio sites.
- Location: extract city/state/country but omit full street addresses for privacy.

### Work Experience
- **company**: exact company name as stated.
- **title**: exact job title as stated.
- **start_date/end_date**: use ISO format YYYY-MM-DD; if only year provided, use YYYY-01-01.
- **is_current**: true if no end date or explicitly stated as current role.
- **achievements**: extract each bullet point or accomplishment as a separate list item.
- **technologies**: extract all tools, frameworks, languages, platforms mentioned for this role.
- **metrics**: extract quantified results as key-value pairs (e.g., {"revenue_increase": "33%"}).

### Education
- **institution**: full name of university/college.
- **degree**: degree type (e.g., "Bachelor of Science", "Master of Arts").
- **field_of_study**: major or concentration.
- **graduation_date**: use ISO format; if only year, use YYYY-05-01 (typical graduation month).
- **gpa**: only if explicitly mentioned and notable (typically 3.5+).
- **honors**: dean's list, cum laude, scholarships, etc.
- **relevant_coursework**: only for recent graduates with <3 years experience.

### Skills
- **name**: exact skill name as stated.
- **category**: classify into: technical, programming, frameworks, tools, languages, soft, domain, other.
- **proficiency**: only if explicitly stated (1-5 scale).
- **years_experience**: only if explicitly mentioned.
- **keywords**: related terms that might appear in job descriptions (for ATS matching).

### Certifications
- **name**: full certification name.
- **acronym**: common abbreviation (e.g., PMP, AWS-SAA, CPA).
- **issuing_organization**: certifying body.
- **date_earned/expiration_date**: use ISO format.
- **credential_id**: if provided.

### Projects
- Distinguish between personal projects and work projects.
- Extract technologies used, role/contribution, and key outcomes.

### Publications & Awards
- Extract verbatim; these are important differentiators.

## Output Format

Return a single JSON object matching the PersonProfile schema. All fields not found should be \
null or empty arrays as appropriate. Do not include any text outside the JSON object."""


def build_profile_extraction_prompt(raw_text: str) -> str:
    """Build the user prompt for profile extraction."""
    schema_json = PersonProfile.model_json_schema()
    return f"""\
Extract structured profile data from the following raw text. Return valid JSON matching the schema.

## JSON Schema Reference

```json
{_format_schema_for_prompt(schema_json)}
```

## Raw Text to Extract From

<raw_text>
{raw_text}
</raw_text>

## Instructions

1. Parse all professional information from the raw text.
2. Return a single JSON object conforming to the PersonProfile schema.
3. Use null for missing optional fields; use empty arrays [] for missing list fields.
4. Dates must be ISO format (YYYY-MM-DD). If only year is known, use January 1st.
5. If a field's format is unclear, make a reasonable interpretation but never fabricate data.
6. For skills, categorize them appropriately based on context.
7. Preserve the original wording of achievements and descriptions.

Return only the JSON object, no additional text or markdown formatting."""


def _format_schema_for_prompt(schema: dict[str, Any]) -> str:
    """Format the schema for inclusion in prompts (compact but readable)."""
    import json

    essential_fields = {
        "properties": schema.get("properties", {}),
        "$defs": {k: v for k, v in schema.get("$defs", {}).items() if "properties" in v},
    }
    return json.dumps(essential_fields, indent=2, default=str)


JOB_DESCRIPTION_EXTRACTION_SYSTEM = """\
You are an expert job posting analyzer. Your task is to parse job descriptions and extract \
structured information for resume tailoring and ATS keyword matching.

## Extraction Principles

1. **Keyword Identification**: Extract all skills, technologies, and qualifications mentioned.
2. **Priority Classification**: Distinguish between required vs. preferred qualifications.
3. **Complete Coverage**: Capture responsibilities, requirements, benefits, and metadata.

## Field Guidelines

### Job Metadata
- **title**: exact job title (may differ from posting title).
- **company**: company name.
- **location**: city/state/country or "Remote".
- **work_arrangement**: onsite/remote/hybrid based on posting.
- **employment_type**: full_time, part_time, contract, etc.
- **experience_level**: intern, entry, mid, senior, lead, principal, executive.

### Requirements Analysis
- **requirements**: each requirement as a separate item with priority level.
- **required_skills**: hard requirements, explicitly stated as must-have.
- **preferred_skills**: nice-to-have skills, often preceded by "preferred" or "bonus".
- **required_education**: minimum education (e.g., "Bachelor's degree in CS or related field").
- **min_years_experience**: explicit minimum years if stated.

### Keyword Extraction for ATS
- Extract all technical skills, tools, frameworks, methodologies.
- Include both acronyms and full forms (e.g., "ML" and "Machine Learning").
- Capture soft skills that are emphasized (e.g., "strong communication").

## Output Format

Return a single JSON object matching the JobDescription schema."""


def build_job_extraction_prompt(job_text: str) -> str:
    """Build the user prompt for job description extraction."""
    from resume_generator.models.job import JobDescription

    schema_json = JobDescription.model_json_schema()
    return f"""\
Extract structured job description data from the following posting. Return valid JSON matching the schema.

## JSON Schema Reference

```json
{_format_schema_for_prompt(schema_json)}
```

## Job Posting Text

<job_posting>
{job_text}
</job_posting>

## Instructions

1. Extract all job requirements, skills, and qualifications.
2. Classify requirements as "required", "preferred", or "nice_to_have".
3. Extract keywords for ATS matching (include synonyms where obvious).
4. Parse experience requirements carefully (e.g., "3-5 years" → min=3, max=5).
5. Return only the JSON object, no additional text.

Return only the JSON object, no additional text or markdown formatting."""


SECTION_EXTRACTION_PROMPTS = {
    "contact": """\
Extract contact information from the following text. Return JSON with:
- full_name (string)
- email (string or null)
- phone (string or null)
- location (string or null, city/state only)
- linkedin_url (string or null)
- github_url (string or null)
- portfolio_url (string or null)

Text: {text}

Return only JSON.""",
    "experience": """\
Extract work experience from the following text. For each position, return:
- company (string)
- title (string)
- location (string or null)
- start_date (YYYY-MM-DD)
- end_date (YYYY-MM-DD or null if current)
- is_current (boolean)
- achievements (list of strings, each bullet point)
- technologies (list of strings)
- metrics (dict of quantified results)

Text: {text}

Return a JSON array of experience objects.""",
    "education": """\
Extract education history from the following text. For each entry, return:
- institution (string)
- degree (string, e.g., "Bachelor of Science")
- field_of_study (string or null)
- graduation_date (YYYY-MM-DD or null)
- gpa (float or null, only if notable)
- honors (list of strings)
- relevant_coursework (list of strings)

Text: {text}

Return a JSON array of education objects.""",
    "skills": """\
Extract skills from the following text. For each skill, return:
- name (string)
- category (one of: technical, programming, frameworks, tools, languages, soft, domain, other)
- proficiency (1-5 or null if not stated)
- years_experience (float or null if not stated)

Text: {text}

Return a JSON array of skill objects.""",
}


ACHIEVEMENT_ENHANCEMENT_PROMPT = """\
You are an expert resume writer. Analyze the following achievement and suggest improvements \
following the Google X-Y-Z formula: "Accomplished [X] as measured by [Y] by doing [Z]".

## Guidelines
- Preserve the factual content; do not fabricate metrics.
- If metrics are missing, suggest where they could be added.
- Use strong action verbs (Spearheaded, Orchestrated, Delivered, Achieved).
- Avoid weak phrases ("Responsible for", "Helped with", "Worked on").

Original Achievement:
{achievement}

Provide:
1. An improved version following X-Y-Z formula (or note what's missing).
2. The action verb used.
3. Whether metrics are present (boolean).
4. Suggested improvements if metrics are missing.

Return JSON:
{{
    "improved": "Enhanced achievement text",
    "action_verb": "verb used",
    "has_metrics": true/false,
    "suggestions": ["list of improvement suggestions"]
}}"""


def build_batch_extraction_prompt(raw_texts: list[str]) -> str:
    """Build prompt for extracting multiple profiles in one call (cost optimization)."""
    texts_formatted = "\n\n---SEPARATOR---\n\n".join(
        f"<document index='{i}'>\n{text}\n</document>" for i, text in enumerate(raw_texts)
    )
    return f"""\
Extract structured profile data from each of the following documents. Return a JSON array where \
each element corresponds to one document in order.

## Documents

{texts_formatted}

## Instructions

1. Process each document independently.
2. Return a JSON array with one PersonProfile object per document.
3. Maintain the same order as the input documents.
4. If a document cannot be parsed, return {{"error": "description"}} for that index.

Return only the JSON array."""

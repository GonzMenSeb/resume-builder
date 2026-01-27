"""Prompt templates for resume content optimization using research-backed principles.

Key principles implemented:
- Google X-Y-Z formula: "Accomplished [X] as measured by [Y], by doing [Z]"
- Strong action verbs (avoid weak phrases like "Responsible for", "Helped with")
- Quantified achievements (2.5x more likely to get interviews)
- ATS keyword optimization (65-80% keyword match rate target)
- Professional summary (50-100 words)
- 3-5 bullet points per position
"""

import json
from typing import Any

ACTION_VERBS_BY_CATEGORY: dict[str, list[str]] = {
    "leadership": [
        "Spearheaded", "Orchestrated", "Directed", "Led", "Championed",
        "Pioneered", "Mobilized", "Cultivated", "Steered", "Mentored",
    ],
    "achievement": [
        "Achieved", "Delivered", "Exceeded", "Surpassed", "Attained",
        "Accomplished", "Captured", "Earned", "Secured", "Won",
    ],
    "creation": [
        "Designed", "Developed", "Engineered", "Architected", "Built",
        "Created", "Established", "Launched", "Initiated", "Founded",
    ],
    "improvement": [
        "Optimized", "Enhanced", "Streamlined", "Accelerated", "Revitalized",
        "Transformed", "Modernized", "Upgraded", "Refined", "Elevated",
    ],
    "management": [
        "Managed", "Oversaw", "Coordinated", "Administered", "Supervised",
        "Executed", "Facilitated", "Governed", "Regulated", "Controlled",
    ],
    "analysis": [
        "Analyzed", "Evaluated", "Assessed", "Investigated", "Diagnosed",
        "Identified", "Mapped", "Measured", "Quantified", "Audited",
    ],
    "communication": [
        "Negotiated", "Presented", "Persuaded", "Influenced", "Advocated",
        "Collaborated", "Partnered", "Liaised", "Mediated", "Articulated",
    ],
    "technical": [
        "Implemented", "Integrated", "Automated", "Deployed", "Configured",
        "Migrated", "Programmed", "Refactored", "Debugged", "Scaled",
    ],
}

WEAK_PHRASES = [
    "responsible for",
    "helped with",
    "worked on",
    "assisted with",
    "participated in",
    "involved in",
    "duties included",
    "tasked with",
    "in charge of",
]

RESUME_OPTIMIZER_SYSTEM = """\
You are an expert resume optimizer specializing in creating S+ tier resumes that maximize \
interview callbacks. You apply research-backed principles to transform raw career data into \
compelling, ATS-optimized content.

## Core Optimization Principles

### The X-Y-Z Formula (Google Standard)
Every achievement should follow: "Accomplished [X] as measured by [Y], by doing [Z]"
- X = What you accomplished (the result)
- Y = Quantified measure of success (the metric)
- Z = How you did it (the method/action)

Example: "Reduced customer churn by 23% (saving $1.2M annually) by implementing a predictive \
analytics model that identified at-risk accounts 30 days earlier."

### Action Verb Rules
1. Start every bullet with a strong action verb (never "Responsible for" or "Helped with")
2. Use past tense for previous roles, present tense for current role
3. Vary verbs across bullets to avoid repetition
4. Match verb strength to achievement significance

### Quantification Guidelines
- Use numbers whenever possible (percentages, dollar amounts, time saved, team sizes)
- Be specific: "15 team members" not "large team"
- Show scale: "serving 2M+ daily active users"
- Demonstrate growth: "from $2M to $8M in ARR (300% increase)"
- If exact metrics unavailable, use reasonable estimates with qualifiers

### ATS Optimization
- Include exact keywords from job descriptions
- Use standard section headers (Experience, Education, Skills)
- Avoid graphics, tables, and special characters in critical fields
- Spell out acronyms at first use with the acronym in parentheses

### Content Structure
- 3-5 bullet points per position (optimal for readability)
- Most impactful achievements first
- Technical skills integrated naturally into achievements
- Professional summary: 50-100 words, tailored to target role

## Output Quality Standards
- Every bullet must provide value; no filler content
- Eliminate redundancy across bullets
- Balance breadth (varied responsibilities) with depth (detailed achievements)
- Maintain authenticity—enhance presentation, never fabricate"""

ACHIEVEMENT_OPTIMIZER_SYSTEM = """\
You are a precision resume bullet optimizer. Your task is to transform raw achievement \
descriptions into high-impact bullets following the X-Y-Z formula.

## Transformation Rules

### Input Analysis
1. Identify the core action/achievement
2. Extract any existing metrics (explicit or implied)
3. Determine the method or approach used
4. Note technical skills and tools mentioned

### X-Y-Z Formula Application
Structure: "Accomplished [X] as measured by [Y], by doing [Z]"

When metrics exist:
- Preserve exact numbers
- Add context (percentages, comparisons, scale)

When metrics are missing:
- Flag for user input OR
- Use qualitative indicators ("significantly", "substantially")
- Suggest where metrics could be added

### Action Verb Selection
Choose verbs that match the achievement type:
- Leadership: Spearheaded, Orchestrated, Led, Championed
- Technical: Engineered, Architected, Implemented, Automated
- Growth: Accelerated, Scaled, Expanded, Grew
- Efficiency: Optimized, Streamlined, Reduced, Eliminated
- Innovation: Pioneered, Invented, Revolutionized, Transformed

### Quality Checks
- Is the result clear and impactful?
- Are metrics specific and credible?
- Does the method demonstrate skill/initiative?
- Is it concise (<25 words if possible)?
- Does it avoid weak phrases ("responsible for", "helped with")?

## Output Format
Return JSON with the optimized bullet and metadata for quality tracking."""

PROFESSIONAL_SUMMARY_SYSTEM = """\
You are an expert at crafting compelling professional summaries that immediately capture \
recruiter attention and establish candidate positioning.

## Summary Formula
[Professional Title] with [X years] of experience [key domain]. [Top 2-3 achievements/skills]. \
[Unique value proposition or career focus].

## Requirements
- Length: 50-100 words (optimal for recruiter scanning)
- Tone: Confident, professional, third-person or implied first-person
- Include: Years of experience, core expertise areas, standout achievements, target role fit
- Avoid: Personal pronouns, generic claims, soft skills without context

## Example
"Senior Software Engineer with 8+ years building scalable distributed systems in fintech. \
Architected real-time payment platforms processing $50B+ annually at 99.99% uptime. \
Proven track record leading teams of 5-12 engineers through complex system migrations. \
Passionate about building fault-tolerant systems that handle millions of daily transactions."

## Customization
When a target job is provided:
- Mirror key terminology from the job description
- Lead with most relevant experience
- Emphasize skills that match required qualifications"""


def build_achievement_optimization_prompt(
    achievement: str,
    role_context: str | None = None,
    target_keywords: list[str] | None = None,
) -> str:
    """Build prompt for optimizing a single achievement bullet."""
    context_section = ""
    if role_context:
        context_section = f"\n## Role Context\n{role_context}\n"

    keywords_section = ""
    if target_keywords:
        keywords_section = f"\n## Target Keywords to Incorporate (if relevant)\n{', '.join(target_keywords)}\n"

    return f"""\
Optimize the following achievement into an X-Y-Z format resume bullet.
{context_section}{keywords_section}
## Original Achievement

<achievement>
{achievement}
</achievement>

## Instructions

1. Identify the core accomplishment (X), measurable result (Y), and method (Z).
2. Rewrite following X-Y-Z formula with a strong action verb.
3. Preserve all factual content—do not fabricate metrics.
4. If metrics are missing, note where they could be added.
5. Keep under 25 words if possible while maintaining impact.

## Output JSON

Return a JSON object with:
{{
    "optimized": "The optimized bullet text",
    "action_verb": "The leading action verb",
    "bullet_type": "xyz | action_result | skill_based | generic",
    "has_metrics": true | false,
    "metrics": {{"metric_name": "value"}} or {{}},
    "keywords": ["keyword1", "keyword2"],
    "improvements_made": ["list of changes"],
    "suggestions": ["suggestions if metrics missing"]
}}"""


def build_bullet_batch_prompt(
    achievements: list[str],
    role_title: str,
    company: str,
    target_keywords: list[str] | None = None,
) -> str:
    """Build prompt for optimizing multiple achievement bullets in one call."""
    bullets_formatted = "\n".join(f"{i+1}. {a}" for i, a in enumerate(achievements))

    keywords_section = ""
    if target_keywords:
        keywords_section = f"""
## Target Keywords (incorporate naturally where relevant)
{', '.join(target_keywords)}
"""

    return f"""\
Optimize the following achievement bullets for a {role_title} position at {company}.
{keywords_section}
## Original Bullets

{bullets_formatted}

## Instructions

1. Transform each bullet using the X-Y-Z formula where possible.
2. Start each with a strong, varied action verb (no repeats).
3. Preserve factual accuracy—never fabricate metrics.
4. Order by impact (most impressive first).
5. Limit to 5 bullets maximum (remove weakest if more).
6. Ensure each bullet is unique and adds value.

## Output JSON

Return a JSON object:
{{
    "bullets": [
        {{
            "text": "Optimized bullet text",
            "action_verb": "Leading verb",
            "bullet_type": "xyz | action_result | skill_based | generic",
            "has_metrics": true | false,
            "metrics": {{}},
            "keywords": [],
            "relevance_score": 0.0-1.0,
            "original_index": 0
        }}
    ],
    "removed_bullets": [
        {{
            "original_index": 3,
            "reason": "Redundant with bullet 1"
        }}
    ],
    "overall_quality_score": 0.0-1.0
}}"""


def build_professional_summary_prompt(
    name: str,
    current_title: str | None,
    years_experience: float | None,
    top_skills: list[str],
    top_achievements: list[str],
    target_job_title: str | None = None,
    target_company: str | None = None,
    target_keywords: list[str] | None = None,
) -> str:
    """Build prompt for generating an optimized professional summary."""
    achievements_text = "\n".join(f"- {a}" for a in top_achievements[:5])
    skills_text = ", ".join(top_skills[:10])

    target_section = ""
    if target_job_title or target_company:
        target_section = f"""
## Target Position
- Job Title: {target_job_title or 'Not specified'}
- Company: {target_company or 'Not specified'}
- Key Keywords: {', '.join(target_keywords or []) or 'None provided'}
"""

    return f"""\
Generate a professional summary for the following candidate.
{target_section}
## Candidate Profile

- Name: {name}
- Current/Recent Title: {current_title or 'Not specified'}
- Years of Experience: {years_experience or 'Not specified'}
- Core Skills: {skills_text}

## Top Achievements

{achievements_text}

## Instructions

1. Write 50-100 words (optimal length for recruiter scanning).
2. Structure: [Title] with [years] experience + [domain]. [Key achievements]. [Value prop].
3. If targeting a specific job, mirror relevant terminology.
4. Use confident, professional tone without personal pronouns.
5. Lead with most impressive or relevant qualifications.
6. Include quantified achievements where available.

## Output JSON

Return a JSON object:
{{
    "summary": "The professional summary text",
    "word_count": 75,
    "keywords_included": ["keyword1", "keyword2"],
    "tailored_for_job": true | false
}}"""


def build_job_tailoring_prompt(
    resume_content: dict[str, Any],
    job_description: dict[str, Any],
) -> str:
    """Build prompt for tailoring resume content to a specific job description."""
    return f"""\
Tailor the following resume content to match the target job description.

## Job Description

<job>
{json.dumps(job_description, indent=2, default=str)}
</job>

## Current Resume Content

<resume>
{json.dumps(resume_content, indent=2, default=str)}
</resume>

## Tailoring Instructions

### Keyword Optimization (target 65-80% match rate)
1. Identify all keywords from job description.
2. Map candidate's equivalent skills/experience to job keywords.
3. Incorporate exact terminology where truthful.

### Bullet Reordering
1. Move most job-relevant achievements to top of each section.
2. De-prioritize (don't delete) less relevant experience.
3. Ensure top 3 bullets per position match key requirements.

### Summary Customization
1. Mirror job title and key qualifications.
2. Lead with experience most relevant to this role.
3. Include 2-3 top keywords naturally.

### Skills Section
1. Reorder to match job requirements priority.
2. Add skill synonyms that match job posting terminology.
3. Remove irrelevant skills only if space is needed.

## Output JSON

Return a JSON object with:
{{
    "tailored_summary": "Updated professional summary",
    "experiences": [
        {{
            "company": "...",
            "title": "...",
            "bullets": ["reordered and optimized bullets"],
            "relevance_score": 0.0-1.0
        }}
    ],
    "skills": {{
        "reordered_groups": [
            {{"category": "...", "skills": ["..."]}}
        ],
        "added_keywords": ["skill synonyms added"],
        "keyword_mapping": {{"job_keyword": "candidate_skill"}}
    }},
    "keyword_analysis": {{
        "job_keywords": ["all extracted keywords"],
        "matched_keywords": ["keywords found in resume"],
        "missing_keywords": ["keywords not covered"],
        "match_rate": 0.75,
        "recommendations": ["suggestions to improve match"]
    }},
    "overall_fit_score": 0.0-1.0
}}"""


def build_skills_optimization_prompt(
    skills: list[dict[str, Any]],
    experiences: list[dict[str, Any]],
    target_keywords: list[str] | None = None,
) -> str:
    """Build prompt for optimizing and grouping skills section."""
    skills_json = json.dumps(skills, indent=2, default=str)
    exp_summary = json.dumps(
        [{"title": e.get("title"), "technologies": e.get("technologies", [])} for e in experiences],
        indent=2,
    )

    keywords_section = ""
    if target_keywords:
        keywords_section = f"""
## Target Keywords (prioritize matching skills)
{', '.join(target_keywords)}
"""

    return f"""\
Optimize and group the following skills for maximum ATS compatibility and visual impact.
{keywords_section}
## Current Skills

{skills_json}

## Technologies from Experience

{exp_summary}

## Instructions

### Grouping Strategy
1. Create logical categories: Languages, Frameworks, Tools, Cloud/Infrastructure, etc.
2. Order categories by relevance to target role.
3. Order skills within categories by proficiency/importance.
4. Limit to 4-6 categories for readability.

### ATS Optimization
1. Include both acronyms and full names for common technologies.
2. Use standard terminology (match job posting conventions).
3. Add closely related skills if candidate clearly has them.

### Quality Rules
1. Remove duplicate or overly similar skills.
2. Remove outdated technologies unless specifically relevant.
3. Consolidate related skills (e.g., "Git, GitHub" → "Git/GitHub").
4. Add technologies from experience that are missing from skills list.

## Output JSON

Return a JSON object:
{{
    "skill_groups": [
        {{
            "category": "Programming Languages",
            "skills": ["Python", "TypeScript", "Go"],
            "priority": 1
        }}
    ],
    "added_skills": ["skills extracted from experience"],
    "removed_skills": [
        {{"skill": "...", "reason": "outdated/duplicate"}}
    ],
    "total_skills_count": 25
}}"""


EXPERIENCE_RELEVANCE_PROMPT = """\
Analyze the relevance of each work experience to the target job and assign relevance scores.

## Target Job
{job_summary}

## Candidate Experiences
{experiences_json}

## Scoring Criteria
- 0.9-1.0: Direct match (same role, same industry)
- 0.7-0.9: Strong match (related role or transferable skills)
- 0.5-0.7: Moderate match (some relevant skills/experience)
- 0.3-0.5: Weak match (minimal overlap)
- 0.0-0.3: Poor match (different field entirely)

## Output JSON
{{
    "scored_experiences": [
        {{
            "company": "...",
            "title": "...",
            "relevance_score": 0.85,
            "relevant_aspects": ["specific things that match"],
            "gaps": ["areas that don't align"]
        }}
    ],
    "recommended_order": [0, 2, 1],
    "experiences_to_expand": [0],
    "experiences_to_condense": [2]
}}"""

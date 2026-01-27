"""Pydantic data models for the resume generator."""

from resume_generator.models.job import (
    EmploymentType,
    ExperienceLevel,
    JobDescription,
    JobRequirement,
    RequirementPriority,
    SalaryRange,
    WorkArrangement,
)
from resume_generator.models.profile import (
    Certification,
    ContactInfo,
    Education,
    Experience,
    PersonProfile,
    Project,
    Skill,
    SkillCategory,
)
from resume_generator.models.resume import (
    BulletType,
    ResumeBullet,
    ResumeCertification,
    ResumeContact,
    ResumeDocument,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeSection,
    ResumeSkillGroup,
    SectionType,
)

__all__ = [
    # Profile models (raw input)
    "Certification",
    "ContactInfo",
    "Education",
    "Experience",
    "PersonProfile",
    "Project",
    "Skill",
    "SkillCategory",
    # Resume models (optimized output)
    "BulletType",
    "ResumeBullet",
    "ResumeCertification",
    "ResumeContact",
    "ResumeDocument",
    "ResumeEducation",
    "ResumeExperience",
    "ResumeProject",
    "ResumeSection",
    "ResumeSkillGroup",
    "SectionType",
    # Job models (for tailoring)
    "EmploymentType",
    "ExperienceLevel",
    "JobDescription",
    "JobRequirement",
    "RequirementPriority",
    "SalaryRange",
    "WorkArrangement",
]

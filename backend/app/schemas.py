from typing import List, Literal
from pydantic import BaseModel, Field

SCORE_DISCLAIMER_TEXT = (
    "AI-estimated match score for guidance and preparation only. "
    "It does not reflect proprietary ATS algorithms or hiring decisions."
)


class MatchedSkill(BaseModel):
    skill: str = Field(
        description="The skill or capability identified in both the resume and the job description."
    )
    evidence: str = Field(
        description="Direct quote or specific context from the resume demonstrating this skill."
    )


class MissingSkill(BaseModel):
    skill: str = Field(
        description="The skill or requirement found in the job description that is missing or not clearly stated in the resume."
    )
    importance: Literal["required", "preferred"] = Field(
        description="Whether this missing skill is a core requirement or a preferred qualification."
    )
    guidance: str = Field(
        description="Practical advice on how the candidate can address or acquire this gap."
    )


class TailoringSuggestion(BaseModel):
    target_section: str = Field(
        description="The section or bullet point in the resume to improve (e.g., 'Work Experience - Recent Role')."
    )
    observation: str = Field(
        description="Critique explaining why the current text is weak or unaligned with the job description."
    )
    suggested_bullet: str = Field(
        description="Rewritten, high-impact bullet point incorporating measurable achievements and keywords."
    )


class InterviewQuestion(BaseModel):
    question: str = Field(
        description="A realistic interview question tailored to the candidate's background and the target role."
    )
    category: str = Field(
        description="The category of question, such as 'Technical Depth', 'Skill Gap Probe', or 'Behavioral'."
    )
    rationale: str = Field(
        description="Explanation of what this question tests and why it is relevant for this specific match."
    )


class AnalysisResponse(BaseModel):
    ai_estimated_score: int = Field(
        ge=0,
        le=100,
        description="AI-estimated overall alignment score between 0 and 100.",
    )
    score_disclaimer: str = Field(
        default=SCORE_DISCLAIMER_TEXT,
        description="Standard disclaimer stating that the score is an AI estimate.",
    )
    summary: str = Field(
        description="A balanced 2-4 sentence executive summary of the candidate's overall fit for the position."
    )
    matched_skills: List[MatchedSkill] = Field(
        default_factory=list,
        description="List of matched skills with supporting quotes/evidence from the resume.",
    )
    missing_skills: List[MissingSkill] = Field(
        default_factory=list,
        description="List of missing or under-emphasized skills categorized as required or preferred.",
    )
    tailoring_suggestions: List[TailoringSuggestion] = Field(
        default_factory=list,
        description="Actionable bullet point rewrites to tailor the resume to the job description.",
    )
    interview_questions: List[InterviewQuestion] = Field(
        default_factory=list,
        description="Targeted interview questions based on the candidate's strengths and gaps.",
    )

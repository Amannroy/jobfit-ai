import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import AnalysisResponse, MatchedSkill, MissingSkill, TailoringSuggestion, InterviewQuestion
from app.services.analyzer_service import GeminiServiceError, GeminiConfigError
from app.services.pdf_service import MAX_FILE_SIZE_BYTES
from tests.test_pdf_service import _build_pdf_bytes, _build_blank_pdf_bytes

client = TestClient(app)

VALID_JOB_DESCRIPTION = (
    "We are seeking an experienced Full Stack Software Engineer to build and scale web applications. "
    "Requirements: 3+ years experience with Python, FastAPI, and React. Experience with Docker, "
    "RESTful API design, and asynchronous programming is highly desired."
)

SAMPLE_RESUME_TEXT = (
    "Senior Software Engineer with 6 years of experience architecting and maintaining production web applications. "
    "Specialized in Python, FastAPI, React, and cloud microservice patterns with high availability and scalability."
)

MOCK_ANALYSIS_RESPONSE = AnalysisResponse(
    ai_estimated_score=88,
    score_disclaimer="AI-estimated match score for guidance and preparation only. It does not reflect proprietary ATS algorithms or hiring decisions.",
    summary="Strong match across Python backend and React frontend capabilities with solid experience.",
    matched_skills=[
        MatchedSkill(
            skill="Python & FastAPI",
            evidence="Resume states: 'Architected async microservices using Python 3.12 and FastAPI handling 5k req/s.'"
        ),
        MatchedSkill(
            skill="React",
            evidence="Resume states: 'Built responsive client dashboards using React and Vite.'"
        )
    ],
    missing_skills=[
        MissingSkill(
            skill="Docker",
            importance="preferred",
            guidance="Highlight any containerized development environments or Dockerfiles created."
        )
    ],
    tailoring_suggestions=[
        TailoringSuggestion(
            target_section="Experience - Software Engineer",
            observation="Current bullet is descriptive rather than quantitative.",
            suggested_bullet="Optimized async endpoint queries, reducing p99 latency by 35%."
        )
    ],
    interview_questions=[
        InterviewQuestion(
            question="Can you explain your approach to handling concurrency in FastAPI?",
            category="Technical Depth",
            rationale="Verifies understanding of Python asyncio and FastAPI async event loops."
        )
    ]
)


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

@patch("app.api.routes.analyze_job_fit")
def test_analyze_success(mock_analyze):
    """1. Test successful end-to-end analysis returning 200 OK and structured response."""
    mock_analyze.return_value = MOCK_ANALYSIS_RESPONSE
    valid_pdf = _build_pdf_bytes(SAMPLE_RESUME_TEXT)

    response = client.post(
        "/api/analyze",
        data={"job_description": VALID_JOB_DESCRIPTION},
        files={"resume": ("resume.pdf", valid_pdf, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ai_estimated_score"] == 88
    assert "AI-estimated" in data["score_disclaimer"]
    assert len(data["matched_skills"]) == 2
    assert data["matched_skills"][0]["skill"] == "Python & FastAPI"
    assert "Resume states:" in data["matched_skills"][0]["evidence"]
    assert len(data["missing_skills"]) == 1
    assert data["missing_skills"][0]["importance"] == "preferred"
    assert len(data["tailoring_suggestions"]) == 1
    assert len(data["interview_questions"]) == 1
    mock_analyze.assert_called_once()


def test_analyze_invalid_pdf():
    """2. Test that corrupted or non-PDF bytes return 400 Bad Request."""
    corrupt_bytes = b"Not a real PDF header or content. Totally broken file data."

    response = client.post(
        "/api/analyze",
        data={"job_description": VALID_JOB_DESCRIPTION},
        files={"resume": ("corrupt.pdf", corrupt_bytes, "application/pdf")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "corrupt or not a valid PDF" in data["detail"]


def test_analyze_oversized_pdf():
    """3. Test that PDF uploads exceeding 5 MB return 413 Payload Too Large."""
    oversized_bytes = b"0" * (MAX_FILE_SIZE_BYTES + 1024)

    response = client.post(
        "/api/analyze",
        data={"job_description": VALID_JOB_DESCRIPTION},
        files={"resume": ("oversized.pdf", oversized_bytes, "application/pdf")},
    )

    assert response.status_code == 413
    data = response.json()
    assert "exceeds the 5 MB limit" in data["detail"]


def test_analyze_insufficient_job_description():
    """4. Test that job descriptions shorter than 50 characters return 400 Bad Request."""
    valid_pdf = _build_pdf_bytes(SAMPLE_RESUME_TEXT)
    short_jd = "Developer needed for web app."

    response = client.post(
        "/api/analyze",
        data={"job_description": short_jd},
        files={"resume": ("resume.pdf", valid_pdf, "application/pdf")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "Job description is too short" in data["detail"]
    assert "at least 50 characters" in data["detail"]


def test_analyze_insufficient_text_pdf():
    """5. Test that scanned / blank PDFs return 400 explaining image-only resumes are unsupported."""
    blank_pdf = _build_blank_pdf_bytes()

    response = client.post(
        "/api/analyze",
        data={"job_description": VALID_JOB_DESCRIPTION},
        files={"resume": ("scanned_resume.pdf", blank_pdf, "application/pdf")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "insufficient extractable text" in data["detail"]
    assert "Scanned or image-only resumes are not supported yet" in data["detail"]


@patch("app.api.routes.analyze_job_fit")
def test_analyze_gemini_service_failure(mock_analyze):
    """6. Test that upstream Gemini service failures return 502 without leaking secrets."""
    mock_analyze.side_effect = GeminiServiceError(
        message="Gemini API error during analysis: Service unavailable. Rate limit reached.",
        status_code=502,
    )
    valid_pdf = _build_pdf_bytes(SAMPLE_RESUME_TEXT)

    response = client.post(
        "/api/analyze",
        data={"job_description": VALID_JOB_DESCRIPTION},
        files={"resume": ("resume.pdf", valid_pdf, "application/pdf")},
    )

    assert response.status_code == 502
    data = response.json()
    assert "Gemini API error during analysis" in data["detail"]
    # Verify no raw secrets or keys are leaked
    assert "AIza" not in data["detail"]
    assert "key=" not in data["detail"]

import json
import pytest
from unittest.mock import MagicMock, patch
from google.genai import errors

from app.schemas import AnalysisResponse, MatchedSkill, MissingSkill
from app.services.analyzer_service import (
    analyze_job_fit,
    verify_model_availability,
    get_gemini_client,
    GeminiConfigError,
    GeminiServiceError,
)

SAMPLE_VALID_RESPONSE_JSON = json.dumps({
    "ai_estimated_score": 85,
    "score_disclaimer": "AI-estimated match score for guidance and preparation only. It does not reflect proprietary ATS algorithms or hiring decisions.",
    "summary": "Candidate demonstrates strong full stack experience aligning with the core requirements.",
    "matched_skills": [
        {
            "skill": "Python & FastAPI",
            "evidence": "Resume states: 'Built high-throughput microservices using FastAPI in Python 3.12.'"
        },
        {
            "skill": "React",
            "evidence": "Resume states: 'Developed interactive dashboards using React 18 and Vite.'"
        }
    ],
    "missing_skills": [
        {
            "skill": "Kubernetes",
            "importance": "preferred",
            "guidance": "Familiarity with container orchestration would strengthen candidate positioning."
        }
    ],
    "tailoring_suggestions": [
        {
            "target_section": "Experience - Senior Developer",
            "observation": "Bullet points emphasize duties rather than measurable results.",
            "suggested_bullet": "Improved API response latency by 40% through async connection pooling."
        }
    ],
    "interview_questions": [
        {
            "question": "How do you handle dependency injection and async state in FastAPI?",
            "category": "Technical Depth",
            "rationale": "Directly evaluates advanced knowledge of the primary backend framework."
        }
    ]
})


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

def test_successful_analysis_parsing():
    """Verify that a valid JSON response from Gemini is correctly parsed into AnalysisResponse."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = SAMPLE_VALID_RESPONSE_JSON
    mock_client.models.generate_content.return_value = mock_response

    result = analyze_job_fit(
        resume_text="Senior Engineer with Python, FastAPI, and React experience.",
        job_description="Seeking a Full Stack Engineer with Python, FastAPI, and React.",
        client=mock_client,
        model_name="gemini-2.5-flash",
    )

    assert isinstance(result, AnalysisResponse)
    assert result.ai_estimated_score == 85
    assert "AI-estimated" in result.score_disclaimer
    assert len(result.matched_skills) == 2
    assert result.matched_skills[0].skill == "Python & FastAPI"
    assert "Resume states:" in result.matched_skills[0].evidence
    assert len(result.missing_skills) == 1
    assert result.missing_skills[0].importance == "preferred"
    assert len(result.tailoring_suggestions) == 1
    assert len(result.interview_questions) == 1


def test_missing_api_key_raises_config_error():
    """Verify that missing API key raises GeminiConfigError without exposing secrets."""
    with pytest.raises(GeminiConfigError) as exc_info:
        get_gemini_client(api_key="")

    assert exc_info.value.status_code == 500
    assert "GEMINI_API_KEY is not configured" in exc_info.value.message


def test_model_verification_success():
    """Verify that verify_model_availability returns True when model exists."""
    mock_client = MagicMock()
    mock_client.models.get.return_value = MagicMock(name="gemini-2.5-flash")

    is_valid = verify_model_availability(client=mock_client, model_name="gemini-2.5-flash")
    assert is_valid is True
    mock_client.models.get.assert_called_once_with(model="gemini-2.5-flash")


def test_model_verification_unsupported_model():
    """Verify that model verification raises GeminiConfigError on invalid model name."""
    mock_client = MagicMock()
    mock_error = errors.APIError(code=404, response_json={"error": {"message": "Model not found"}})
    mock_client.models.get.side_effect = mock_error

    with pytest.raises(GeminiConfigError) as exc_info:
        verify_model_availability(client=mock_client, model_name="non-existent-model")

    assert exc_info.value.status_code == 502
    assert "unavailable or not supported" in exc_info.value.message


def test_invalid_llm_response_schema_raises_service_error():
    """Verify that malformed or schema-violating JSON raises GeminiServiceError."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Missing required fields like summary, matched_skills, etc.
    mock_response.text = '{"ai_estimated_score": 50}'
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_job_fit(
            resume_text="Some resume text",
            job_description="Some job description",
            client=mock_client,
        )

    assert exc_info.value.status_code == 502
    assert "did not conform to the expected analysis schema" in exc_info.value.message


def test_empty_llm_response_raises_service_error():
    """Verify that empty response text raises GeminiServiceError."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = None
    mock_client.models.generate_content.return_value = mock_response

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_job_fit(
            resume_text="Some resume text",
            job_description="Some job description",
            client=mock_client,
        )

    assert exc_info.value.status_code == 502
    assert "empty response" in exc_info.value.message


def test_gemini_api_error_handling():
    """Verify that upstream API errors are caught and re-raised cleanly without leaking keys."""
    mock_client = MagicMock()
    mock_error = errors.APIError(code=503, response_json={"error": {"message": "The service is temporarily overloaded."}})
    mock_client.models.generate_content.side_effect = mock_error

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_job_fit(
            resume_text="Resume text",
            job_description="Job description",
            client=mock_client,
        )

    assert exc_info.value.status_code == 502
    assert "Gemini API error during analysis" in exc_info.value.message


def test_empty_inputs_rejected():
    """Verify that empty resume or JD arguments raise ValueError immediately."""
    with pytest.raises(ValueError, match="Resume text cannot be empty"):
        analyze_job_fit("", "Some job description")

    with pytest.raises(ValueError, match="Job description cannot be empty"):
        analyze_job_fit("Some resume text", "")

import json
import logging
from typing import Optional
from pydantic import ValidationError
from google import genai
from google.genai import types, errors

from app.config import settings
from app.schemas import AnalysisResponse

logger = logging.getLogger(__name__)


class GeminiConfigError(Exception):
    """Raised when API key or model configuration is missing or invalid."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GeminiServiceError(Exception):
    """Raised when the Gemini API encounters a runtime failure or invalid response."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _sanitize_error(message: str, secret: Optional[str]) -> str:
    """Helper to ensure raw secrets or keys are never included in error messages."""
    if secret and secret in message:
        return message.replace(secret, "[REDACTED_API_KEY]")
    return message


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """
    Creates and returns an authenticated Google Gen AI client.
    Raises GeminiConfigError if no key is configured.
    """
    key = api_key if api_key is not None else settings.gemini_api_key
    if not key or not key.strip():
        raise GeminiConfigError(
            "GEMINI_API_KEY is not configured. Please set the GEMINI_API_KEY environment variable in your .env file.",
            status_code=500,
        )
    return genai.Client(api_key=key.strip())


def verify_model_availability(
    client: Optional[genai.Client] = None,
    model_name: Optional[str] = None,
) -> bool:
    """
    Verifies that the configured model is available and supported for the API key.
    Raises GeminiConfigError if the model cannot be accessed.
    """
    target_model = model_name or settings.gemini_model
    if not target_model or not target_model.strip():
        raise GeminiConfigError("GEMINI_MODEL is not configured.", status_code=500)

    active_client = client or get_gemini_client()

    try:
        active_client.models.get(model=target_model.strip())
        return True
    except errors.APIError as e:
        safe_msg = _sanitize_error(str(e.message if hasattr(e, "message") else e), settings.gemini_api_key)
        raise GeminiConfigError(
            f"Configured Gemini model '{target_model}' is unavailable or not supported: {safe_msg}",
            status_code=502,
        ) from e
    except Exception as e:
        safe_msg = _sanitize_error(str(e), settings.gemini_api_key)
        raise GeminiConfigError(
            f"Failed to verify model '{target_model}': {safe_msg}",
            status_code=500,
        ) from e


def analyze_job_fit(
    resume_text: str,
    job_description: str,
    client: Optional[genai.Client] = None,
    model_name: Optional[str] = None,
) -> AnalysisResponse:
    """
    Analyzes resume text against a job description using Gemini with structured JSON output.
    Enforces evidence-based skill extraction and AI estimate score labeling.
    """
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text cannot be empty.")
    if not job_description or not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    target_model = model_name or settings.gemini_model
    active_client = client or get_gemini_client()

    system_instruction = (
        "You are an objective, expert technical recruiter and resume strategist. "
        "Analyze the candidate's resume against the target job description with high precision.\n\n"
        "Key Guidelines:\n"
        "1. AI Estimated Score: Provide an overall alignment score between 0 and 100 based strictly "
        "on demonstrated technical match, years of experience, and role responsibilities.\n"
        "2. Evidence Requirement: For every item in matched_skills, you MUST provide explicit evidence "
        "quoted or contextually grounded in the resume text. Do NOT assume or hallucinate skills not stated.\n"
        "3. Missing Skills: Identify key requirements from the job description not present in the resume. "
        "Categorize each as 'required' or 'preferred' and provide practical advice.\n"
        "4. Tailoring Suggestions: Provide actionable, high-impact bullet point rewrites.\n"
        "5. Interview Questions: Generate relevant interview questions addressing both technical depth "
        "and any identified experience gaps."
    )

    prompt = (
        f"JOB DESCRIPTION:\n{job_description.strip()}\n\n"
        f"--- CANDIDATE RESUME TEXT ---\n{resume_text.strip()}\n\n"
        "Perform a thorough match evaluation following the requested JSON schema."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=AnalysisResponse,
    )

    try:
        response = active_client.models.generate_content(
            model=target_model.strip(),
            contents=prompt,
            config=config,
        )
    except errors.APIError as e:
        safe_msg = _sanitize_error(str(e.message if hasattr(e, "message") else e), settings.gemini_api_key)
        raise GeminiServiceError(
            f"Gemini API error during analysis: {safe_msg}",
            status_code=502,
        ) from e
    except Exception as e:
        safe_msg = _sanitize_error(str(e), settings.gemini_api_key)
        raise GeminiServiceError(
            f"Unexpected error communicating with Gemini API: {safe_msg}",
            status_code=500,
        ) from e

    # Extract response text
    response_text = response.text if hasattr(response, "text") and response.text else None
    if not response_text:
        raise GeminiServiceError(
            "Gemini returned an empty response. Please verify the prompt or try again.",
            status_code=502,
        )

    # Validate against Pydantic schema
    try:
        parsed_result = AnalysisResponse.model_validate_json(response_text)
        return parsed_result
    except (ValidationError, json.JSONDecodeError) as e:
        logger.error("Failed to parse Gemini response into AnalysisResponse schema")
        raise GeminiServiceError(
            "Gemini response did not conform to the expected analysis schema.",
            status_code=502,
        ) from e

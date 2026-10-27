import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.schemas import AnalysisResponse
from app.services.pdf_service import extract_text_from_pdf, PDFValidationError
from app.services.analyzer_service import (
    analyze_job_fit,
    GeminiConfigError,
    GeminiServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

MIN_JOB_DESC_LENGTH = 50


@router.get("/health", tags=["Health"])
async def health_check():
    """
    Basic health check endpoint to verify backend service status.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "configured_model": settings.gemini_model,
    }


@router.post("/api/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_resume_endpoint(
    resume: UploadFile = File(..., description="PDF resume file (max 5 MB)"),
    job_description: str = Form(..., description="Target job description text (min 50 chars)"),
):
    """
    Analyzes an in-memory PDF resume against a provided job description.
    Never persists uploaded files or sensitive content to disk.
    """
    # 1. Validate job description first before consuming file bytes
    clean_jd = job_description.strip() if job_description else ""
    if len(clean_jd) < MIN_JOB_DESC_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Job description is too short ({len(clean_jd)} characters). "
                f"Please provide at least {MIN_JOB_DESC_LENGTH} characters for a meaningful analysis."
            ),
        )

    # 2. Read PDF bytes directly in memory
    try:
        pdf_bytes = await resume.read()
    except Exception as e:
        logger.error("Failed to read uploaded resume bytes: %s", type(e).__name__)
        raise HTTPException(
            status_code=400,
            detail="Could not read uploaded file bytes. Please try uploading the file again.",
        ) from e

    # 3. Validate and extract text in memory (never written to disk)
    try:
        resume_text = extract_text_from_pdf(
            pdf_bytes=pdf_bytes,
            filename=resume.filename,
            content_type=resume.content_type,
        )
    except PDFValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    # 4. Perform structured AI analysis with Gemini
    try:
        analysis_result = analyze_job_fit(
            resume_text=resume_text,
            job_description=clean_jd,
        )
        return analysis_result
    except GeminiConfigError as e:
        logger.error("Gemini configuration issue: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except GeminiServiceError as e:
        logger.error("Gemini service failure: %s", e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except HTTPException:
        raise
    except Exception as e:
        # Sanitize internal errors completely
        logger.error("Unexpected error during analysis: %s", type(e).__name__)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while analyzing the resume. Please try again later.",
        ) from e

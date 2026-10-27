from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.routes import router
from app.limiter import limiter

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Backend API for JobFit AI — Resume & Job Description Analyzer",
)

# Attach rate limiter instance to application state
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Returns a user-friendly HTTP 429 response when client exceeds rate limits.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded: maximum 5 requests per minute allowed. Please wait a moment before trying again."
        },
    )


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.app_name} API",
        "health_check": "/health",
        "docs": "/docs",
    }

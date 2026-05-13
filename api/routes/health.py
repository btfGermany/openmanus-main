"""
Health check API routes.

System health including Redis, LLM, and worker connectivity.
"""

from fastapi import APIRouter
import redis

from api.config import api_config
from api.models import HealthResponse


router = APIRouter(prefix="/api/v1", tags=["health"])


def check_redis() -> str:
    """Check Redis connectivity."""
    try:
        r = redis.from_url(api_config.redis.url)
        r.ping()
        r.close()
        return "healthy"
    except Exception:
        return "unhealthy"


def check_llm() -> str:
    """Check LLM connectivity."""
    # TODO: Implement actual LLM check
    # For now, check that config is valid
    try:
        from app.config import config
        llm_cfg = config.llm.get("default")
        if llm_cfg and llm_cfg.api_key:
            return "healthy"
        return "missing_api_key"
    except Exception:
        return "unavailable"


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health_check():
    """Check system health."""
    redis_status = check_redis()
    llm_status = check_llm()
    
    overall = "healthy" if redis_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall,
        redis=redis_status,
        llm=llm_status,
        version=api_config.api.version,
    )


@router.get(
    "/ready",
    response_model=dict,
)
async def readiness_check():
    """Check if service is ready to accept traffic."""
    # Check Redis
    redis_status = check_redis()
    if redis_status != "healthy":
        return {"ready": False, "reason": "redis_unavailable"}
    
    return {"ready": True}


@router.get(
    "/live",
    response_model=dict,
)
async def liveness_check():
    """Check if service is alive."""
    return {"alive": True}
"""
Admin API routes.

API key management and usage analytics.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from api.config import api_config
from api.core.auth import api_key_store, rate_limiter
from api.models import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyWithSecret,
    ErrorResponse,
    UsageStats,
)


router = APIRouter(prefix="/admin", tags=["admin"])


def validate_admin_key(request: Request) -> bool:
    """Validate admin API key."""
    admin_key = api_config.apikey.admin_key
    
    # If no admin key configured, allow access for development
    if not admin_key:
        return True
    
    provided = request.headers.get("X-Admin-Key") or request.headers.get("X-API-Key")
    if not provided:
        raise HTTPException(status_code=401, detail="Missing admin key")
    
    if provided != admin_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    return True


@router.post(
    "/keys",
    response_model=ApiKeyWithSecret,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
    },
)
async def create_api_key(req: Request, request: ApiKeyCreateRequest):
    """Generate a new API key."""
    validate_admin_key(req)
    
    # Set defaults
    if request.rate_limit_rpm <= 0:
        request.rate_limit_rpm = api_config.apikey.default_rate_limit_rpm
    if request.rate_limit_rph <= 0:
        request.rate_limit_rph = api_config.apikey.default_rate_limit_rph
    if request.concurrent_tasks <= 0:
        request.concurrent_tasks = api_config.apikey.default_concurrent_tasks
    
    key = api_key_store.create_key(request)
    return key


@router.get(
    "/keys",
    response_model=list[ApiKeyResponse],
)
async def list_api_keys(req: Request):
    """List all API keys with usage stats."""
    validate_admin_key(req)
    return api_key_store.list_keys()


@router.delete(
    "/keys/{key_id}",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def revoke_api_key(req: Request, key_id: UUID):
    """Revoke an API key."""
    validate_admin_key(req)
    
    success = api_key_store.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Also reset rate limits
    rate_limiter.reset(key_id)
    
    return {"revoked": True, "key_id": str(key_id)}


@router.get(
    "/usage",
    response_model=UsageStats,
)
async def get_usage_stats(req: Request):
    """Get aggregate usage dashboard."""
    validate_admin_key(req)
    return api_key_store.get_usage_stats()


@router.post(
    "/keys/{key_id}/reset-rate-limit",
)
async def reset_rate_limit(req: Request, key_id: UUID):
    """Reset rate limits for a key."""
    validate_admin_key(req)
    rate_limiter.reset(key_id)
    return {"reset": True, "key_id": str(key_id)}
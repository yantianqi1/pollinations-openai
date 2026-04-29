from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from typing import Optional

from app.config import settings, update_settings
from app.services.admin_auth import (
    INVALID_ADMIN_KEY,
    clear_admin_cookie,
    is_valid_admin_key,
    require_admin_session,
    require_configured_admin_key,
    set_admin_cookie,
)
from app.services.image_cache import image_cache
from app.services.pollinations import request_stats

router = APIRouter(prefix="/admin", tags=["admin"])


def _mask_key(key: str) -> str:
    if len(key) <= 4:
        return "***"
    return key[:2] + "***" + key[-2:]


class AdminLoginRequest(BaseModel):
    key: str


@router.post("/login")
async def login(request: Request, response: Response, body: AdminLoginRequest):
    require_configured_admin_key()
    if not is_valid_admin_key(body.key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_ADMIN_KEY,
        )
    set_admin_cookie(request, response, body.key)
    return {"authenticated": True}


@router.post("/logout")
async def logout(request: Request, response: Response):
    clear_admin_cookie(request, response)
    return {"authenticated": False}


@router.get("/session")
async def get_session(_: None = Depends(require_admin_session)):
    return {"authenticated": True}


@router.get("/stats")
async def get_stats(_: None = Depends(require_admin_session)):
    cache = image_cache.stats()
    return {
        **cache,
        "total_requests": request_stats["total"],
        "success": request_stats["success"],
        "fail": request_stats["fail"],
        "api_key_masked": _mask_key(settings.pollinations_api_key),
    }


@router.get("/config")
async def get_config(_: None = Depends(require_admin_session)):
    return {
        "pollinations_api_key": _mask_key(settings.pollinations_api_key),
        "image_cache_ttl": settings.image_cache_ttl,
        "image_cache_max_size": settings.image_cache_max_size,
        "default_nologo": settings.default_nologo,
        "default_private": settings.default_private,
    }


class ConfigUpdateRequest(BaseModel):
    pollinations_api_key: Optional[str] = None
    image_cache_ttl: Optional[int] = None
    image_cache_max_size: Optional[int] = None
    default_nologo: Optional[bool] = None
    default_private: Optional[bool] = None


@router.post("/config")
async def post_config(
    body: ConfigUpdateRequest,
    _: None = Depends(require_admin_session),
):
    data = body.model_dump(exclude_none=True)
    updated = update_settings(data)
    return {"updated": updated}

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.config import settings, update_settings
from app.services.image_cache import image_cache
from app.services.pollinations import request_stats

router = APIRouter(prefix="/admin", tags=["admin"])


def _mask_key(key: str) -> str:
    if len(key) <= 4:
        return "***"
    return key[:2] + "***" + key[-2:]


@router.get("/stats")
async def get_stats():
    cache = image_cache.stats()
    return {
        **cache,
        "total_requests": request_stats["total"],
        "success": request_stats["success"],
        "fail": request_stats["fail"],
        "api_key_masked": _mask_key(settings.pollinations_api_key),
    }


@router.get("/config")
async def get_config():
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
async def post_config(body: ConfigUpdateRequest):
    data = body.model_dump(exclude_none=True)
    updated = update_settings(data)
    return {"updated": updated}

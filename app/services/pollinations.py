import logging
import time
from typing import Dict, List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_http_client: Optional[httpx.AsyncClient] = None
_models_cache: Optional[Tuple[List[Dict], float]] = None

# Request counters
request_stats = {"total": 0, "success": 0, "fail": 0}


async def get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    return _http_client


async def close_client() -> None:
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def fetch_image_models() -> List[Dict]:
    global _models_cache

    if _models_cache is not None:
        models, cached_at = _models_cache
        if time.time() - cached_at < settings.model_cache_ttl:
            return models

    client = await get_client()
    try:
        resp = await client.get(settings.pollinations_models_url)
        resp.raise_for_status()
        models = resp.json()
        _models_cache = (models, time.time())
        return models
    except Exception:
        logger.exception("Failed to fetch models from Pollinations")
        if _models_cache is not None:
            return _models_cache[0]
        return []


async def generate_image(url: str) -> Tuple[bytes, str]:
    client = await get_client()
    headers = {"Authorization": f"Bearer {settings.pollinations_api_key}"}

    request_stats["total"] += 1
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        request_stats["fail"] += 1
        raise

    request_stats["success"] += 1
    content_type = resp.headers.get("content-type", "image/jpeg")
    if ";" in content_type:
        content_type = content_type.split(";")[0].strip()

    return resp.content, content_type

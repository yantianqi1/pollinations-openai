from typing import Optional, Tuple

import httpx

from app.config import settings

_http_client: Optional[httpx.AsyncClient] = None

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

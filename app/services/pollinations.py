import json
import re
from typing import Any, Optional, Tuple

import httpx

from app.config import settings

ERROR_STATUS_PATTERN = re.compile(r"HTTP error! status: (\d+)")
DETAIL_MESSAGE_PATTERN = re.compile(r'"msg":"([^"]+)')
ERROR_PREVIEW_CHARS = 200

_http_client: Optional[httpx.AsyncClient] = None

# Request counters
request_stats = {"total": 0, "success": 0, "fail": 0}


class PollinationsError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _extract_status_code(message: str, default: int) -> int:
    match = ERROR_STATUS_PATTERN.search(message)
    if match is None:
        return default
    return int(match.group(1))


def _extract_detail_message(payload: dict[str, Any]) -> Optional[str]:
    detail = payload.get("detail")
    if not isinstance(detail, list) or not detail:
        return None

    first_item = detail[0]
    if not isinstance(first_item, dict):
        return None

    message = first_item.get("msg")
    if not isinstance(message, str):
        return None
    return message


def _normalize_nested_message(message: str, default_status: int) -> tuple[int, str]:
    status_code = _extract_status_code(message, default_status)
    _, _, body = message.partition("body: ")
    if not body:
        return status_code, message

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        match = DETAIL_MESSAGE_PATTERN.search(body)
        if match is None:
            return status_code, message
        return status_code, f"HTTP {status_code}: {match.group(1)}"

    detail_message = _extract_detail_message(payload)
    if detail_message is None:
        return status_code, message
    return status_code, f"HTTP {status_code}: {detail_message}"


def _extract_error(response: httpx.Response) -> PollinationsError:
    fallback_message = f"HTTP {response.status_code} from Pollinations"

    try:
        payload = response.json()
    except ValueError:
        preview = response.text[:ERROR_PREVIEW_CHARS].strip()
        if preview:
            fallback_message = f"HTTP {response.status_code}: {preview}"
        return PollinationsError(fallback_message, response.status_code)

    error = payload.get("error")
    if not isinstance(error, dict):
        return PollinationsError(fallback_message, response.status_code)

    raw_message = error.get("message")
    if not isinstance(raw_message, str):
        return PollinationsError(fallback_message, response.status_code)

    try:
        nested_payload = json.loads(raw_message)
    except json.JSONDecodeError:
        status_code, message = _normalize_nested_message(raw_message, response.status_code)
        return PollinationsError(message, status_code)

    nested_message = nested_payload.get("message")
    if not isinstance(nested_message, str):
        return PollinationsError(fallback_message, response.status_code)

    status_code, message = _normalize_nested_message(
        nested_message,
        response.status_code,
    )
    return PollinationsError(message, status_code)


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
    except httpx.HTTPStatusError as exc:
        request_stats["fail"] += 1
        raise _extract_error(exc.response) from exc
    except httpx.HTTPError as exc:
        request_stats["fail"] += 1
        raise PollinationsError("Failed to reach Pollinations", 502) from exc

    request_stats["success"] += 1
    content_type = resp.headers.get("content-type", "image/jpeg")
    if ";" in content_type:
        content_type = content_type.split(";")[0].strip()

    return resp.content, content_type

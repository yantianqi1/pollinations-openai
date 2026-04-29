from secrets import compare_digest
from typing import Optional

from fastapi import HTTPException, Request, Response, status

from app.config import settings

ADMIN_COOKIE_NAME = "zimage_admin_session"
ADMIN_SESSION_MAX_AGE_SECONDS = 60 * 60 * 12
ADMIN_LOGIN_REQUIRED = "Admin login required"
ADMIN_KEY_NOT_CONFIGURED = "Admin panel key is not configured"
INVALID_ADMIN_KEY = "Invalid admin key"


def has_admin_session(request: Request) -> bool:
    return is_valid_admin_key(request.cookies.get(ADMIN_COOKIE_NAME))


def is_valid_admin_key(candidate: Optional[str]) -> bool:
    configured_key = settings.admin_panel_key
    if not configured_key or candidate is None:
        return False
    return compare_digest(candidate, configured_key)


def require_admin_session(request: Request) -> None:
    if has_admin_session(request):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ADMIN_LOGIN_REQUIRED,
    )


def require_configured_admin_key() -> None:
    if settings.admin_panel_key:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=ADMIN_KEY_NOT_CONFIGURED,
    )


def set_admin_cookie(request: Request, response: Response, admin_key: str) -> None:
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=admin_key,
        max_age=ADMIN_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=_is_secure_request(request),
        samesite="strict",
    )


def clear_admin_cookie(request: Request, response: Response) -> None:
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        httponly=True,
        secure=_is_secure_request(request),
        samesite="strict",
    )


def _is_secure_request(request: Request) -> bool:
    return request.url.scheme == "https"

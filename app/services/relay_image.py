import logging
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.services.image_cache import image_cache
from app.services.model_presets import resolve_model_request
from app.services.pollinations import generate_image
from app.services.url_builder import build_pollinations_image_url, parse_size

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RelayImageResult:
    url: str
    revised_prompt: str


def client_error_status(status_code: int) -> int:
    if 400 <= status_code < 500:
        return status_code
    return 502


def _resolve_relay_base(request_base_url: str) -> str:
    relay_base = settings.relay_base_url.rstrip("/")
    if relay_base:
        return relay_base
    return request_base_url.rstrip("/")


async def create_relay_image(
    prompt: str,
    model: str,
    size: str,
    seed: Optional[int],
    request_base_url: str,
) -> RelayImageResult:
    resolved_model, resolved_size = resolve_model_request(model, size)
    width, height = parse_size(resolved_size)
    upstream_url = build_pollinations_image_url(
        prompt=prompt,
        model=resolved_model,
        width=width,
        height=height,
        seed=seed,
    )
    logger.info(
        "Generating image: requested_model=%s upstream_model=%s size=%sx%s",
        model,
        resolved_model,
        width,
        height,
    )
    image_bytes, content_type = await generate_image(upstream_url)
    image_id = image_cache.store(image_bytes, content_type)
    relay_base = _resolve_relay_base(request_base_url)
    return RelayImageResult(
        url=f"{relay_base}/images/{image_id}",
        revised_prompt=prompt,
    )

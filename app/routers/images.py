import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.config import settings
from app.schemas.images import (
    ImageDataItem,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from app.services.image_cache import image_cache
from app.services.model_presets import resolve_model_request
from app.services.pollinations import PollinationsError, generate_image
from app.services.url_builder import build_pollinations_image_url, parse_size

logger = logging.getLogger(__name__)

router = APIRouter()


def _client_error_status(status_code: int) -> int:
    if 400 <= status_code < 500:
        return status_code
    return 502


@router.post("/v1/images/generations", response_model=ImageGenerationResponse)
async def create_image(request: Request, body: ImageGenerationRequest):
    resolved_model, resolved_size = resolve_model_request(body.model, body.size)
    width, height = parse_size(resolved_size)

    url = build_pollinations_image_url(
        prompt=body.prompt,
        model=resolved_model,
        width=width,
        height=height,
        seed=body.seed,
    )

    logger.info(
        "Generating image: requested_model=%s upstream_model=%s size=%sx%s",
        body.model,
        resolved_model,
        width,
        height,
    )

    try:
        image_bytes, content_type = await generate_image(url)
    except PollinationsError as exc:
        logger.warning("Image generation rejected: %s", exc)
        raise HTTPException(
            status_code=_client_error_status(exc.status_code),
            detail=exc.message,
        ) from exc
    except Exception:
        logger.exception("Image generation failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to generate image from Pollinations",
        )

    image_id = image_cache.store(image_bytes, content_type)

    relay_base = settings.relay_base_url.rstrip("/")
    if not relay_base:
        relay_base = str(request.base_url).rstrip("/")
    image_url = f"{relay_base}/images/{image_id}"

    return ImageGenerationResponse(
        created=int(time.time()),
        data=[ImageDataItem(url=image_url, revised_prompt=body.prompt)],
    )


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    result = image_cache.get(image_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Image not found or expired")
    image_bytes, content_type = result
    return Response(content=image_bytes, media_type=content_type)

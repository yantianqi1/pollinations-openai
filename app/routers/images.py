import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.schemas.images import (
    ImageDataItem,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from app.services.image_cache import image_cache
from app.services.pollinations import PollinationsError
from app.services.relay_image import client_error_status, create_relay_image

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/images/generations", response_model=ImageGenerationResponse)
async def create_image(request: Request, body: ImageGenerationRequest):
    try:
        result = await create_relay_image(
            prompt=body.prompt,
            model=body.model,
            size=body.size,
            seed=body.seed,
            request_base_url=str(request.base_url),
        )
    except PollinationsError as exc:
        logger.warning("Image generation rejected: %s", exc)
        raise HTTPException(
            status_code=client_error_status(exc.status_code),
            detail=exc.message,
        ) from exc
    except Exception:
        logger.exception("Image generation failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to generate image from Pollinations",
        )

    return ImageGenerationResponse(
        created=int(time.time()),
        data=[ImageDataItem(url=result.url, revised_prompt=result.revised_prompt)],
    )


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    result = image_cache.get(image_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Image not found or expired")
    image_bytes, content_type = result
    return Response(content=image_bytes, media_type=content_type)

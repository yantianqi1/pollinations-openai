from fastapi import APIRouter, HTTPException

from app.schemas.models import ModelListResponse
from app.services.model_presets import merge_model_items
from app.services.pollinations import PollinationsError
from app.services.upstream_models import (
    build_upstream_image_model_items,
    fetch_upstream_image_models,
)

router = APIRouter()


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    try:
        upstream_models = await fetch_upstream_image_models()
        upstream_items = build_upstream_image_model_items(upstream_models)
    except PollinationsError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    return ModelListResponse(data=merge_model_items(upstream_items))

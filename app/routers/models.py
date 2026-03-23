import logging

from fastapi import APIRouter

from app.schemas.models import ModelItem, ModelListResponse
from app.services.pollinations import fetch_image_models

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    raw_models = await fetch_image_models()

    data = []
    for m in raw_models:
        if isinstance(m, str):
            data.append(ModelItem(id=m))
        elif isinstance(m, dict) and "name" in m:
            data.append(ModelItem(id=m["name"]))

    return ModelListResponse(data=data)

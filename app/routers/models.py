from fastapi import APIRouter

from app.schemas.models import ModelListResponse
from app.services.model_presets import build_public_model_items

router = APIRouter()


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    return ModelListResponse(data=build_public_model_items())

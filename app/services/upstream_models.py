from typing import Any

import httpx

from app.config import settings
from app.schemas.models import ModelItem
from app.services.pollinations import PollinationsError, get_client

IMAGE_MODALITY = "image"
INVALID_MODELS_PAYLOAD_ERROR = "Invalid Pollinations image models payload"
FETCH_MODELS_ERROR = "Failed to fetch Pollinations image models"


async def fetch_upstream_image_models() -> list[dict[str, Any]]:
    client = await get_client()

    try:
        response = await client.get(settings.pollinations_models_url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PollinationsError(FETCH_MODELS_ERROR, 502) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PollinationsError(INVALID_MODELS_PAYLOAD_ERROR, 502) from exc

    if not isinstance(payload, list):
        raise PollinationsError(INVALID_MODELS_PAYLOAD_ERROR, 502)
    return payload


def build_upstream_image_model_items(
    upstream_models: list[dict[str, Any]],
) -> list[ModelItem]:
    model_items: list[ModelItem] = []
    for upstream_model in upstream_models:
        model_name = _extract_model_name(upstream_model)
        output_modalities = _extract_output_modalities(upstream_model)
        if IMAGE_MODALITY not in output_modalities:
            continue
        model_items.append(ModelItem(id=model_name))
    return model_items


def _extract_model_name(upstream_model: dict[str, Any]) -> str:
    model_name = upstream_model.get("name")
    if not isinstance(model_name, str) or not model_name:
        raise PollinationsError(INVALID_MODELS_PAYLOAD_ERROR, 502)
    return model_name


def _extract_output_modalities(upstream_model: dict[str, Any]) -> list[str]:
    output_modalities = upstream_model.get("output_modalities")
    if not isinstance(output_modalities, list):
        raise PollinationsError(INVALID_MODELS_PAYLOAD_ERROR, 502)
    if any(not isinstance(modality, str) for modality in output_modalities):
        raise PollinationsError(INVALID_MODELS_PAYLOAD_ERROR, 502)
    return output_modalities

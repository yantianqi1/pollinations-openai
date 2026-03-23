from dataclasses import dataclass
from typing import Final

from app.schemas.models import ModelItem

UPSTREAM_ZIMAGE_MODEL: Final[str] = "zimage"
RELAY_OWNER: Final[str] = "relay"


@dataclass(frozen=True)
class ModelPreset:
    alias: str
    upstream_model: str
    size: str


MODEL_PRESETS: Final[tuple[ModelPreset, ...]] = (
    ModelPreset("z-image-1024x1024", UPSTREAM_ZIMAGE_MODEL, "1024x1024"),
    ModelPreset("z-image-1216x832", UPSTREAM_ZIMAGE_MODEL, "1216x832"),
    ModelPreset("z-image-1216x688", UPSTREAM_ZIMAGE_MODEL, "1216x688"),
    ModelPreset("z-image-688x1216", UPSTREAM_ZIMAGE_MODEL, "688x1216"),
    ModelPreset("z-image-832x1216", UPSTREAM_ZIMAGE_MODEL, "832x1216"),
)

PRESET_BY_ALIAS: Final[dict[str, ModelPreset]] = {
    preset.alias: preset for preset in MODEL_PRESETS
}


def build_public_model_items() -> list[ModelItem]:
    return [
        ModelItem(id=preset.alias, owned_by=RELAY_OWNER) for preset in MODEL_PRESETS
    ]


def merge_model_items(upstream_items: list[ModelItem]) -> list[ModelItem]:
    merged_items: list[ModelItem] = []
    seen_ids: set[str] = set()

    for item in [*build_public_model_items(), *upstream_items]:
        if item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        merged_items.append(item)

    return merged_items


def resolve_model_request(model: str, size: str) -> tuple[str, str]:
    preset = PRESET_BY_ALIAS.get(model)
    if preset is None:
        return model, size
    return preset.upstream_model, preset.size

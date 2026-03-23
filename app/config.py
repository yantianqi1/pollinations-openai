from typing import Any, Dict

from pydantic_settings import BaseSettings

UPDATABLE_FIELDS = {
    "pollinations_api_key",
    "image_cache_ttl",
    "image_cache_max_size",
    "default_nologo",
    "default_private",
}


class Settings(BaseSettings):
    pollinations_api_key: str
    pollinations_base_url: str = "https://gen.pollinations.ai/image"
    pollinations_models_url: str = "https://gen.pollinations.ai/image/models"
    port: int = 8000
    host: str = "0.0.0.0"
    image_cache_ttl: int = 1800
    image_cache_max_size: int = 200
    model_cache_ttl: int = 3600
    default_nologo: bool = True
    default_private: bool = True
    relay_base_url: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()


def update_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    updated = {}
    for key, value in data.items():
        if key in UPDATABLE_FIELDS and value is not None:
            setattr(settings, key, value)
            updated[key] = value
    return updated

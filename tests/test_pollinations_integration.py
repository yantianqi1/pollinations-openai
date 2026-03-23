import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.config import settings
from app.routers.images import create_image
from app.routers.models import list_models
from app.schemas.images import ImageGenerationRequest
from app.services.url_builder import build_pollinations_image_url

PUBLIC_MODEL_ALIASES = [
    "z-image-1024x1024",
    "z-image-1216x832",
    "z-image-1216x688",
    "z-image-688x1216",
    "z-image-832x1216",
    "z-image-1560x2048",
    "z-image-1260x2048",
    "z-image-2048x1260",
    "z-image-2048x1560",
]


class BuildPollinationsImageUrlTest(unittest.TestCase):
    def test_uses_current_gen_image_endpoint(self) -> None:
        original_base_url = settings.pollinations_base_url
        settings.pollinations_base_url = "https://gen.pollinations.ai/image"

        try:
            url = build_pollinations_image_url(
                prompt="a cute cat",
                model="flux",
                width=256,
                height=128,
                seed=42,
            )
        finally:
            settings.pollinations_base_url = original_base_url

        self.assertEqual(
            url,
            (
                "https://gen.pollinations.ai/image/a%20cute%20cat"
                "?model=flux&width=256&height=128&seed=42"
                "&nologo=true&private=true&safe=false"
            ),
        )


class DownstreamModelAliasTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_models_returns_only_alias_presets(self) -> None:
        response = await list_models()

        self.assertEqual(
            [item.id for item in response.data],
            PUBLIC_MODEL_ALIASES,
        )

    async def test_create_image_maps_alias_to_zimage_and_fixed_size(self) -> None:
        original_relay_base_url = settings.relay_base_url
        settings.relay_base_url = "https://relay.example"

        body = ImageGenerationRequest(
            model="z-image-1216x832",
            prompt="a cute cat",
            size="512x512",
            seed=42,
        )

        try:
            with patch(
                "app.routers.images.generate_image",
                AsyncMock(return_value=(b"img", "image/png")),
            ) as mock_generate, patch(
                "app.routers.images.image_cache.store",
                Mock(return_value="img123"),
            ):
                response = await create_image(Mock(), body)
        finally:
            settings.relay_base_url = original_relay_base_url

        mock_generate.assert_awaited_once_with(
            (
                "https://gen.pollinations.ai/image/a%20cute%20cat"
                "?model=zimage&width=1216&height=832&seed=42"
                "&nologo=true&private=true&safe=false"
            )
        )
        self.assertEqual(response.data[0].url, "https://relay.example/images/img123")

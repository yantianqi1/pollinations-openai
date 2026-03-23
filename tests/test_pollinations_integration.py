import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.config import settings
from app.services import pollinations
from app.services.url_builder import build_pollinations_image_url


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
                "&nologo=true&private=true"
            ),
        )


class FetchImageModelsTest(unittest.IsolatedAsyncioTestCase):
    async def test_reads_models_from_current_image_models_endpoint(self) -> None:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [{"name": "flux"}]

        mock_client = Mock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.pollinations.get_client",
            AsyncMock(return_value=mock_client),
        ):
            pollinations._models_cache = None
            models = await pollinations.fetch_image_models()

        mock_client.get.assert_awaited_once_with(
            "https://gen.pollinations.ai/image/models"
        )
        self.assertEqual(models, [{"name": "flux"}])

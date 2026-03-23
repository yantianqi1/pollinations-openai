import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routers.images import create_image
from app.routers.models import list_models
from app.schemas.images import ImageGenerationRequest
from app.services.pollinations import PollinationsError, generate_image
from app.services.relay_image import create_relay_image
from app.services.url_builder import build_pollinations_image_url

PUBLIC_MODEL_ALIASES = [
    "z-image-1024x1024",
    "z-image-1216x832",
    "z-image-1216x688",
    "z-image-688x1216",
    "z-image-832x1216",
]
UPSTREAM_IMAGE_MODELS = [
    {"name": "flux", "output_modalities": ["image"]},
    {"name": "gptimage", "output_modalities": ["image"]},
    {"name": "veo", "output_modalities": ["video"]},
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
    async def test_list_models_merges_aliases_with_upstream_image_models(self) -> None:
        with patch(
            "app.routers.models.fetch_upstream_image_models",
            AsyncMock(
                return_value=[
                    *UPSTREAM_IMAGE_MODELS,
                ]
            ),
            create=True,
        ):
            response = await list_models()

        self.assertEqual(
            [item.id for item in response.data],
            [*PUBLIC_MODEL_ALIASES, "flux", "gptimage"],
        )
        self.assertNotIn("veo", [item.id for item in response.data])

    async def test_create_relay_image_maps_alias_to_zimage_and_fixed_size(self) -> None:
        original_relay_base_url = settings.relay_base_url
        settings.relay_base_url = "https://relay.example"

        try:
            with patch(
                "app.services.relay_image.generate_image",
                AsyncMock(return_value=(b"img", "image/png")),
            ) as mock_generate, patch(
                "app.services.relay_image.image_cache.store",
                Mock(return_value="img123"),
            ):
                response = await create_relay_image(
                    prompt="a cute cat",
                    model="z-image-1216x832",
                    size="512x512",
                    seed=42,
                    request_base_url="http://testserver/",
                )
        finally:
            settings.relay_base_url = original_relay_base_url

        mock_generate.assert_awaited_once_with(
            (
                "https://gen.pollinations.ai/image/a%20cute%20cat"
                "?model=zimage&width=1216&height=832&seed=42"
                "&nologo=true&private=true&safe=false"
            )
        )
        self.assertEqual(response.url, "https://relay.example/images/img123")

    async def test_create_image_surfaces_upstream_validation_error(self) -> None:
        body = ImageGenerationRequest(
            model="z-image-1024x1024",
            prompt="a cute cat",
            size="1024x1024",
            seed=42,
        )

        with patch(
            "app.routers.images.create_relay_image",
            AsyncMock(
                side_effect=PollinationsError(
                    message="HTTP 422: upstream rejected request",
                    status_code=422,
                )
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await create_image(Mock(), body)

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(
            ctx.exception.detail,
            "HTTP 422: upstream rejected request",
        )


class _FakeHttpClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    async def get(self, *_args, **_kwargs) -> httpx.Response:
        return self._response


class PollinationsErrorParsingTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_image_extracts_nested_validation_error(self) -> None:
        nested_body = {
            "detail": [
                {
                    "msg": (
                        "Value error, Requested 2048x1560 = 3,194,880 pixels exceeds "
                        "limit of 2,359,296 pixels. Max: 1536x1536 or equivalent area."
                    )
                }
            ]
        }
        outer_message = json.dumps(
            {
                "error": "Internal Server Error",
                "message": f"HTTP error! status: 422, body: {json.dumps(nested_body)}",
            }
        )
        response = httpx.Response(
            status_code=500,
            json={"success": False, "error": {"message": outer_message}},
            request=httpx.Request("GET", "https://gen.pollinations.ai/image/test"),
        )

        with patch(
            "app.services.pollinations.get_client",
            AsyncMock(return_value=_FakeHttpClient(response)),
        ):
            with self.assertRaises(PollinationsError) as ctx:
                await generate_image("https://gen.pollinations.ai/image/test")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(
            str(ctx.exception),
            (
                "HTTP 422: Value error, Requested 2048x1560 = 3,194,880 pixels "
                "exceeds limit of 2,359,296 pixels. Max: 1536x1536 or equivalent "
                "area."
            ),
        )

    async def test_generate_image_extracts_message_from_truncated_payload(self) -> None:
        truncated_message = (
            "HTTP error! status: 422, body: "
            '{"detail":[{"type":"value_error","loc":["body","height"],'
            '"msg":"Value error, Requested 2048x1560 = 3,194,880 pixels '
            'exceeds limit of 2,359,296 pixels. Max: 1536x1536 or equivalent '
            'area.","input":1560,'
        )
        response = httpx.Response(
            status_code=500,
            json={"success": False, "error": {"message": truncated_message}},
            request=httpx.Request("GET", "https://gen.pollinations.ai/image/test"),
        )

        with patch(
            "app.services.pollinations.get_client",
            AsyncMock(return_value=_FakeHttpClient(response)),
        ):
            with self.assertRaises(PollinationsError) as ctx:
                await generate_image("https://gen.pollinations.ai/image/test")

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(
            str(ctx.exception),
            (
                "HTTP 422: Value error, Requested 2048x1560 = 3,194,880 pixels "
                "exceeds limit of 2,359,296 pixels. Max: 1536x1536 or equivalent "
                "area."
            ),
        )


class ChatCompletionCompatTest(unittest.TestCase):
    def test_chat_completions_returns_markdown_image(self) -> None:
        response = httpx.Response(
            status_code=200,
            content=b"image-bytes",
            headers={"content-type": "image/png"},
            request=httpx.Request("GET", "https://gen.pollinations.ai/image/test"),
        )

        with patch(
            "app.services.pollinations.get_client",
            AsyncMock(return_value=_FakeHttpClient(response)),
        ):
            client = TestClient(app)
            result = client.post(
                "/v1/chat/completions",
                json={
                    "model": "z-image-1216x832",
                    "messages": [{"role": "user", "content": "a cute cat"}],
                },
            )

        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body["object"], "chat.completion")
        self.assertEqual(body["model"], "z-image-1216x832")
        self.assertIn("![image](", body["choices"][0]["message"]["content"])
        self.assertIn("http://testserver/images/", body["choices"][0]["message"]["content"])

    def test_chat_completions_supports_text_content_parts(self) -> None:
        response = httpx.Response(
            status_code=200,
            content=b"image-bytes",
            headers={"content-type": "image/png"},
            request=httpx.Request("GET", "https://gen.pollinations.ai/image/test"),
        )

        with patch(
            "app.services.pollinations.get_client",
            AsyncMock(return_value=_FakeHttpClient(response)),
        ):
            client = TestClient(app)
            result = client.post(
                "/v1/chat/completions",
                json={
                    "model": "z-image-1024x1024",
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": "portrait photo"}],
                        }
                    ],
                },
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["choices"][0]["message"]["role"], "assistant")

    def test_chat_completions_streams_sse_chunks(self) -> None:
        response = httpx.Response(
            status_code=200,
            content=b"image-bytes",
            headers={"content-type": "image/png"},
            request=httpx.Request("GET", "https://gen.pollinations.ai/image/test"),
        )

        with patch(
            "app.services.pollinations.get_client",
            AsyncMock(return_value=_FakeHttpClient(response)),
        ):
            client = TestClient(app)
            result = client.post(
                "/v1/chat/completions",
                json={
                    "model": "z-image-1216x832",
                    "messages": [{"role": "user", "content": "a cute cat"}],
                    "stream": True,
                },
            )

        self.assertEqual(result.status_code, 200)
        self.assertIn("text/event-stream", result.headers["content-type"])
        self.assertIn("chat.completion.chunk", result.text)
        self.assertIn("data: [DONE]", result.text)

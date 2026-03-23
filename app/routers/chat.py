import logging
import time

from fastapi import APIRouter, HTTPException, Request

from app.schemas.chat import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionRequestMessage,
    ChatCompletionResponse,
    ChatCompletionResponseMessage,
)
from app.services.pollinations import PollinationsError
from app.services.relay_image import client_error_status, create_relay_image

logger = logging.getLogger(__name__)

STREAM_NOT_SUPPORTED_MESSAGE = "Streaming is not supported for image chat completions"
NO_USER_MESSAGE_ERROR = "A user text message is required for image generation"

router = APIRouter()


def _message_text(message: ChatCompletionRequestMessage) -> str:
    if isinstance(message.content, str):
        return message.content.strip()
    text_parts = [
        part.text.strip()
        for part in message.content
        if part.type == "text" and part.text and part.text.strip()
    ]
    return "\n".join(text_parts)


def _extract_prompt(messages: list[ChatCompletionRequestMessage]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        prompt = _message_text(message)
        if prompt:
            return prompt
    raise HTTPException(status_code=400, detail=NO_USER_MESSAGE_ERROR)


def _image_markdown(image_url: str) -> str:
    return f"![image]({image_url})"


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: Request, body: ChatCompletionRequest):
    if body.stream:
        raise HTTPException(status_code=400, detail=STREAM_NOT_SUPPORTED_MESSAGE)

    prompt = _extract_prompt(body.messages)
    try:
        result = await create_relay_image(
            prompt=prompt,
            model=body.model,
            size=body.size,
            seed=body.seed,
            request_base_url=str(request.base_url),
        )
    except PollinationsError as exc:
        logger.warning("Chat image generation rejected: %s", exc)
        raise HTTPException(
            status_code=client_error_status(exc.status_code),
            detail=exc.message,
        ) from exc
    except Exception:
        logger.exception("Chat image generation failed")
        raise HTTPException(
            status_code=502,
            detail="Failed to generate image from Pollinations",
        )

    return ChatCompletionResponse(
        created=int(time.time()),
        model=body.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionResponseMessage(
                    content=_image_markdown(result.url),
                )
            )
        ],
    )

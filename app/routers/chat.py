import json
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

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

STREAM_CONTENT_TYPE = "text/event-stream"
STREAM_DONE = "data: [DONE]\n\n"
NO_USER_MESSAGE_ERROR = "A user text message is required for image generation"
CHAT_COMPLETION_CHUNK_OBJECT = "chat.completion.chunk"

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


def _chunk_payload(
    completion_id: str,
    created: int,
    model: str,
    delta: dict[str, str],
    finish_reason: Optional[str],
) -> str:
    payload = {
        "id": completion_id,
        "object": CHAT_COMPLETION_CHUNK_OBJECT,
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _streaming_body(model: str, content: str):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    yield _chunk_payload(
        completion_id=completion_id,
        created=created,
        model=model,
        delta={"role": "assistant"},
        finish_reason=None,
    )
    yield _chunk_payload(
        completion_id=completion_id,
        created=created,
        model=model,
        delta={"content": content},
        finish_reason=None,
    )
    yield _chunk_payload(
        completion_id=completion_id,
        created=created,
        model=model,
        delta={},
        finish_reason="stop",
    )
    yield STREAM_DONE


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: Request, body: ChatCompletionRequest):
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

    content = _image_markdown(result.url)
    if body.stream:
        return StreamingResponse(
            _streaming_body(body.model, content),
            media_type=STREAM_CONTENT_TYPE,
        )

    return ChatCompletionResponse(
        created=int(time.time()),
        model=body.model,
        choices=[
            ChatCompletionChoice(
                message=ChatCompletionResponseMessage(
                    content=content,
                )
            )
        ],
    )

import uuid
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class ChatCompletionContentPart(BaseModel):
    type: str
    text: Optional[str] = None


class ChatCompletionRequestMessage(BaseModel):
    role: str
    content: Union[str, List[ChatCompletionContentPart]]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionRequestMessage]
    size: str = "1024x1024"
    seed: Optional[int] = None
    stream: bool = False


class ChatCompletionResponseMessage(BaseModel):
    role: str = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionResponseMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)

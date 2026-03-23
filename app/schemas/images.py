from typing import Optional

from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    model: str = "flux"
    prompt: str
    n: int = Field(default=1, ge=1, le=1)
    size: str = "1024x1024"
    seed: Optional[int] = None


class ImageDataItem(BaseModel):
    url: str
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: list[ImageDataItem]

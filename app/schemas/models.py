from pydantic import BaseModel


class ModelItem(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "pollinations"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelItem]

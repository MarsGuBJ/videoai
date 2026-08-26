"""以图搜人 / 文本检索 DTO。"""

from pydantic import BaseModel


class PersonSearchImageResponse(BaseModel):
    imageUrl: str
    imagePath: str


class PersonSearchDetectRequest(BaseModel):
    imageUrl: str


class PersonSearchByBboxRequest(BaseModel):
    imageUrl: str
    bbox: list[dict] | None = None
    searchMethod: str = "reid"
    startTime: str | None = None
    endTime: str | None = None
    similarityThreshold: float = 0.6
    topK: int = 10


class TextSearchQueryRequest(BaseModel):
    message: str
    startTime: str | None = None
    endTime: str | None = None
    location: str | None = None
    page: int = 1
    pageSize: int = 10

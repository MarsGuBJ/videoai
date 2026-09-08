"""搜索关键词 DTO（对外契约 camelCase）。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SearchType = Literal["text_video", "text_image"]


class SearchKeywordOut(BaseModel):
    id: str
    keyword: str
    searchType: str
    createdAt: datetime


class SearchKeywordStatItem(BaseModel):
    keyword: str
    searchType: str
    count: int
    lastSearchedAt: datetime

"""复核类型 DTO（对外契约 camelCase）。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1)
    injectEvent: str = ""
    remark: str = ""
    llmConfigId: str | None = None


class ReviewTypeUpdate(BaseModel):
    """全字段可选；缺省（None）表示保留原值。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    prompt: str | None = Field(default=None, min_length=1)
    injectEvent: str | None = None
    remark: str | None = None
    llmConfigId: str | None = None


class ReviewTypeOut(BaseModel):
    """对外返回的复核类型。"""

    id: str
    name: str
    code: str
    prompt: str
    injectEvent: str
    remark: str
    llmConfigId: str | None
    createdAt: datetime
    updatedAt: datetime

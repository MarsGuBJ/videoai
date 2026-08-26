"""事件信息 DTO（对外契约 camelCase）。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventLevel = Literal["低", "中", "高"]


class EventAttrItem(BaseModel):
    """事件自定义属性键值对。"""

    key: str
    value: str


class EventInfoCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=100)
    level: EventLevel = "低"
    category: str = ""
    mark: str = ""
    iconName: str = ""
    source: str = ""
    eventSource: str = ""
    algorithmCode: str = ""
    attrs: list[EventAttrItem] = Field(default_factory=list)
    enabled: bool = True


class EventInfoUpdate(BaseModel):
    """全字段可选；缺省表示保留原值。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=100)
    level: EventLevel | None = None
    category: str | None = None
    mark: str | None = None
    iconName: str | None = None
    source: str | None = None
    eventSource: str | None = None
    algorithmCode: str | None = None
    attrs: list[EventAttrItem] | None = None
    sortOrder: int | None = None
    enabled: bool | None = None


class EventInfoOut(BaseModel):
    id: str
    name: str
    code: str
    level: EventLevel
    category: str
    mark: str
    iconName: str
    source: str
    eventSource: str
    algorithmCode: str
    attrs: list[EventAttrItem]
    sortOrder: int
    enabled: bool
    createdAt: datetime
    updatedAt: datetime

"""事件推送任务 DTO（对外契约 camelCase；description 序列化为 desc）。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_EXPIRE_DAYS = 30

PushTaskType = Literal["mq", "http"]


class PushTaskCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=200)
    type: PushTaskType = "http"
    address: str = ""
    mqAddr: str = ""
    mqUser: str = ""
    mqPass: str = ""
    token: str = ""
    expireDays: int = Field(default=DEFAULT_EXPIRE_DAYS, ge=1)
    eventSource: str = ""
    eventTypes: str = ""
    description: str = Field(default="", alias="desc")
    enabled: bool = True


class PushTaskUpdate(BaseModel):
    """全字段可选；mqPass 传空字符串或缺省表示保留原值。"""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: PushTaskType | None = None
    address: str | None = None
    mqAddr: str | None = None
    mqUser: str | None = None
    mqPass: str | None = None
    token: str | None = None
    expireDays: int | None = Field(default=None, ge=1)
    eventSource: str | None = None
    eventTypes: str | None = None
    description: str | None = Field(default=None, alias="desc")
    enabled: bool | None = None


class PushTaskOut(BaseModel):
    """对外返回的推送任务；mqPass 掩码，另附 mqPassConfigured 标记；token 明文。"""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    type: PushTaskType
    address: str
    mqAddr: str
    mqUser: str
    mqPass: str
    mqPassConfigured: bool
    token: str
    expireDays: int
    eventSource: str
    eventTypes: str
    description: str = Field(serialization_alias="desc")
    enabled: bool
    createdAt: datetime
    updatedAt: datetime

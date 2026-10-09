"""录像存储绑定代理 DTO。"""

from pydantic import BaseModel, Field, field_validator


class StorageBindRequest(BaseModel):
    """绑定请求：一批摄像头绑定到同一台录像存储主机。"""

    cameraIds: list[str] = Field(min_length=1)
    storageHost: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("storageHost", "username", "password", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        """必填文本先去掉首尾空白，避免只填空格绕过 min_length。"""
        return value.strip() if isinstance(value, str) else value


class StorageUnbindRequest(BaseModel):
    cameraIds: list[str] = Field(min_length=1)


class StorageBindingItem(BaseModel):
    """单条绑定关系（MCP 侧的 host 字段在此映射为 storageHost）。"""

    cameraId: str
    storageHost: str
    username: str


class ResolvedStorageBindingItem(BaseModel):
    """摄像头实际生效的录像存储设备（含显式绑定与回放链路解析出的设备）。

    bound 标记是否为显式绑定（只有显式绑定可通过 unbind 解除）。
    """

    cameraId: str
    storageHost: str
    bound: bool


class StorageBindSkippedItem(BaseModel):
    """绑定校验未通过被跳过的摄像头及原因。"""

    cameraId: str
    reason: str


class StorageBindResponse(BaseModel):
    bound: int
    skipped: list[StorageBindSkippedItem] = Field(default_factory=list)


class StorageUnbindResponse(BaseModel):
    unbound: int

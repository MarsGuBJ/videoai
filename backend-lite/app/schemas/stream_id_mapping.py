"""流ID映射代理 DTO。"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class StreamIdMappingRow(BaseModel):
    """单条流ID映射导入行。"""

    streamId: str = Field(min_length=1)
    cameraHost: str = Field(min_length=1)

    @field_validator("streamId", "cameraHost", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        """必填文本先去掉首尾空白，避免只填空格绕过 min_length。"""
        return value.strip() if isinstance(value, str) else value


class StreamIdImportCvr(BaseModel):
    """导入时使用的 CVR 连接信息。"""

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    @field_validator("host", "username", "password", mode="before")
    @classmethod
    def _strip_required_text(cls, value: object) -> object:
        """必填文本先去掉首尾空白，避免只填空格绕过 min_length。"""
        return value.strip() if isinstance(value, str) else value


class StreamIdImportRequest(BaseModel):
    """导入请求：一批流ID映射行 + 目标 CVR 连接信息。"""

    rows: list[StreamIdMappingRow] = Field(min_length=1)
    cvr: StreamIdImportCvr


class StreamIdImportResponse(BaseModel):
    """导入结果：成功条数与跳过明细（row 为 MCP 原样回显的导入行）。"""

    imported: int
    skipped: list[dict[str, Any]] = Field(default_factory=list)


class StreamIdMappingItem(BaseModel):
    """单条流ID映射（摄像头流ID与其所在 CVR 的关联）。"""

    cameraHost: str
    streamId: str
    cvrHost: str
    cvrPort: int
    username: str

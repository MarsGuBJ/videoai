"""大模型配置 DTO（对外契约 camelCase）。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
DEFAULT_FPS = 1

DeployType = Literal["cloud", "local"]


class LlmConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    baseUrl: str = Field(min_length=1, max_length=500)
    model: str = Field(default="", max_length=200)
    apiKey: str = ""
    deployType: DeployType = "cloud"
    timeout: int = Field(default=DEFAULT_TIMEOUT_SECONDS, ge=10, le=120)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    maxTokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=1)
    fps: int = Field(default=DEFAULT_FPS, ge=1)


class LlmConfigUpdate(BaseModel):
    """全字段可选；apiKey 传空字符串或缺省表示保留原值。"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    baseUrl: str | None = Field(default=None, min_length=1, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    apiKey: str | None = None
    deployType: DeployType | None = None
    timeout: int | None = Field(default=None, ge=10, le=120)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    maxTokens: int | None = Field(default=None, ge=1)
    fps: int | None = Field(default=None, ge=1)


class LlmConfigOut(BaseModel):
    """对外返回的大模型配置；apiKey 掩码，另附 apiKeyConfigured 标记。"""

    id: str
    name: str
    baseUrl: str
    model: str
    apiKey: str
    apiKeyConfigured: bool
    deployType: DeployType
    timeout: int
    temperature: float
    maxTokens: int
    fps: int
    createdAt: datetime
    updatedAt: datetime


class LlmTestResult(BaseModel):
    ok: bool
    latencyMs: int | None = None
    statusCode: int | None = None
    error: str | None = None
    checkedAt: datetime

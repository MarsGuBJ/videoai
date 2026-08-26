"""模型管理（Triton）DTO。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelRegisterRequest(BaseModel):
    name: str
    displayName: str
    repositoryPath: str | None = None
    modelType: str
    description: str | None = None


class ModelResponse(BaseModel):
    id: UUID
    name: str
    displayName: str
    repositoryPath: str | None = None
    modelType: str
    description: str | None = None
    state: str
    createdAt: datetime
    updatedAt: datetime


class ModelGpuResponse(BaseModel):
    modelName: str
    gpuIds: list[int]
    configPath: str


class ModelGpuUpdateRequest(BaseModel):
    gpuIds: list[int] = Field(min_length=1)

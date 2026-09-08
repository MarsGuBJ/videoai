"""定时复核任务 DTO（对外契约 camelCase）。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewSchedulePayload(BaseModel):
    """创建/更新共用入参；cron 合法性在路由层用 croniter 校验。"""

    name: str = Field(min_length=1, max_length=200)
    reviewTypeId: str = Field(min_length=1)
    cron: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    batchSize: int = Field(default=50, ge=1, le=500)


class ReviewScheduleOut(BaseModel):
    """对外返回的定时复核任务。"""

    id: str
    name: str
    cron: str
    enabled: bool
    batchSize: int
    reviewTypeId: str
    reviewTypeName: str
    reviewTypeCode: str
    lastRunAt: datetime | None
    lastResult: str
    createdAt: datetime
    updatedAt: datetime

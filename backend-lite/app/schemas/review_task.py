"""复核任务 DTO（对外契约 camelCase）。"""

from datetime import datetime

from pydantic import BaseModel


class ReviewTaskOut(BaseModel):
    """对外返回的复核任务。"""

    id: str
    reviewTypeId: str
    reviewTypeName: str
    reviewTypeCode: str
    llmConfigId: str
    llmConfigName: str
    imageUrl: str
    status: str
    verdict: str
    reason: str
    createdAt: datetime
    updatedAt: datetime
